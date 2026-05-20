#!/usr/bin/env python3
"""
Patch ImageSlot to wrap its inner aspect-ratio container in an <a target="_blank">
when slot.link is set. Then set SLOTS['2.5'].real (cover image) + .link (PDF path).

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

OLD_OPEN = """data-slot-kind={slot.kind}>
      <div style={{
        position:'relative',
        aspectRatio: ratio,
        width:'100%',
        borderRadius:12,
        overflow:'hidden',
        background: isFilled ? (dark?'rgba(0,0,0,0.4)':'#fff') : palette.bg,
        border: isFilled ? `1px solid ${dark?'rgba(255,255,255,0.18)':'rgba(46, 90, 72, 0.22)'}` : `1px dashed ${palette.border}`,
        display:'flex',
        flexDirection:'column',
        justifyContent:'space-between',
        padding: isFilled ? 0 : (compact?'12px 14px':'16px 18px'),
      }}>"""

NEW_OPEN = """data-slot-kind={slot.kind}>
      {React.createElement(slot.link ? 'a' : 'div', {
        href: slot.link || undefined,
        target: slot.link ? '_blank' : undefined,
        rel: slot.link ? 'noopener noreferrer' : undefined,
        style: {
          position:'relative',
          aspectRatio: ratio,
          width:'100%',
          borderRadius:12,
          overflow:'hidden',
          background: isFilled ? (dark?'rgba(0,0,0,0.4)':'#fff') : palette.bg,
          border: isFilled ? `1px solid ${dark?'rgba(255,255,255,0.18)':'rgba(46, 90, 72, 0.22)'}` : `1px dashed ${palette.border}`,
          display:'flex',
          flexDirection:'column',
          justifyContent:'space-between',
          padding: isFilled ? 0 : (compact?'12px 14px':'16px 18px'),
          textDecoration:'none',
          color:'inherit',
          cursor: slot.link ? 'pointer' : undefined,
        }
      }, ["""

# Trick: when we open the React.createElement(... , [ ... ]) we must close it after
# the existing children. So we also need to replace the matching `</div>` with `])}`.
# The closing </div> that pairs with the opener is at a known position relative to other text.
# Use a unique tail marker (a comment right after the children block).

# Approach: find the original close `</div>` immediately followed by the caption block opener.
# The figure's structure (from prior inspection) is:
#   <div ...> ...children... </div>
#   {showCaption && ...}    <-- after the inner div
# We'll anchor on " </div>\n      {showCaption" or similar. Let's find it dynamically.

INNER_DIV_CLOSE_CANDIDATES = [
    "</div>\n      {showCaption",     # best guess
    "</div>\n    {showCaption",
    "</div>\n      {/* Caption",
]


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try: return json.loads(raw), m.start(1), m.end(1)
    except: return json.loads(raw.replace('\\"','"').replace('\\u002F','/').replace('\\u003E','>').replace('\\u003C','<')), m.start(1), m.end(1)


def decode(e):
    raw = base64.b64decode(e["data"])
    if e.get("compressed"): raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"): raw = gzip.compress(raw)
    return {"mime": template["mime"], "compressed": template.get("compressed", False), "data": base64.b64encode(raw).decode("ascii")}


def js_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def find_inner_div_close(js, start_idx):
    """Walk forward from start_idx, tracking <div> depth, until we find the matching </div>."""
    depth = 1
    i = start_idx
    while i < len(js):
        next_open = js.find("<div", i)
        next_close = js.find("</div>", i)
        if next_close == -1:
            return -1
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return next_close  # position of </div>
            i = next_close + 6
    return -1


CLOSE_SENTINEL = "      </div>\n      {/* Tag below figure"

def patch_image_slot(js: str):
    if "React.createElement(slot.link ? 'a' : 'div'" in js:
        print("Already patched")
        return js, False
    if OLD_OPEN not in js:
        print("ERROR: opening div block not found")
        return js, False
    if CLOSE_SENTINEL not in js:
        print("ERROR: close sentinel not found")
        return js, False

    open_pos = js.find(OLD_OPEN)
    open_end = open_pos + len(OLD_OPEN)
    close_pos = js.find(CLOSE_SENTINEL, open_end)
    # Replace: opening tag → NEW_OPEN; closing "      </div>\n" → "      ])}\n"
    new_js = (
        js[:open_pos]
        + NEW_OPEN
        + js[open_end:close_pos]
        + "      ])}\n      {/* Tag below figure"
        + js[close_pos + len(CLOSE_SENTINEL):]
    )
    return new_js, True


def patch_slot_25(js: str):
    """Set SLOTS['2.5'] real and link (idempotent — strips prior and re-adds)."""
    real_path = "images/Page2/2.5_mdpi_cover.jpg"
    link_path = "images/Page2/2.5_mdpi_paper.pdf"
    # Find entry
    pat = re.compile(r"'2\.5'\s*:\s*\{[^{}]*\}")
    m = pat.search(js)
    if not m:
        print("SLOTS['2.5'] not found"); return js
    entry = m.group(0)
    # Strip prior real:/link:
    for k in ("real", "link"):
        entry = re.sub(r",\s*" + k + r":'(?:\\'|[^'])*'", "", entry)
    new_entry = entry[:-1].rstrip() + ", real:" + js_str(real_path) + ", link:" + js_str(link_path) + " }"
    return js[:m.start()] + new_entry + js[m.end():]


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded {BUNDLE_UUID[:8]}: {len(js)} chars")

    js, did = patch_image_slot(js)
    print(f"ImageSlot anchor wrap: {'applied' if did else 'no-op'}")

    js = patch_slot_25(js)
    print("SLOTS['2.5'] updated with real + link")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
