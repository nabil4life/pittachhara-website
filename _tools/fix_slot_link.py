#!/usr/bin/env python3
"""
RECOVERY: the previous patch_slot_link.py wrapped JSX children in a [array],
which is a syntax error in JSX. This script replaces that broken
`{React.createElement(...,[` opening and the matching `])}` close with a
valid IIFE pattern that uses a dynamic JSX wrapper tag (`<Wrap ...>...</Wrap>`),
which Babel can transform correctly.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

BROKEN_OPEN = """      {React.createElement(slot.link ? 'a' : 'div', {
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

FIXED_OPEN = """      {(() => {
        const Wrap = slot.link ? 'a' : 'div';
        return (
          <Wrap
            href={slot.link || undefined}
            target={slot.link ? '_blank' : undefined}
            rel={slot.link ? 'noopener noreferrer' : undefined}
            style={{
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
            }}
          >"""

BROKEN_CLOSE = "      ])}"
FIXED_CLOSE = "          </Wrap>\n        );\n      })()}"


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try: return json.loads(raw), m.start(1), m.end(1)
    except: return json.loads(raw.replace('\\"','"').replace('\\u002F','/').replace('\\u003E','>').replace('\\u003C','<')), m.start(1), m.end(1)


def decode(e):
    r = base64.b64decode(e["data"])
    if e.get("compressed"): r = gzip.decompress(r)
    return r.decode("utf-8")


def encode(t, tpl):
    r = t.encode("utf-8")
    if tpl.get("compressed"): r = gzip.compress(r)
    return {"mime": tpl["mime"], "compressed": tpl.get("compressed", False), "data": base64.b64encode(r).decode("ascii")}


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded {BUNDLE_UUID[:8]}: {len(js)} chars")

    if BROKEN_OPEN not in js:
        if "const Wrap = slot.link" in js:
            print("Already fixed (idempotent no-op)")
            return
        print("ERROR: broken opening not found")
        return
    if BROKEN_CLOSE not in js:
        print("ERROR: broken closing not found")
        return

    js = js.replace(BROKEN_OPEN, FIXED_OPEN)
    js = js.replace(BROKEN_CLOSE, FIXED_CLOSE, 1)
    print("Replaced broken React.createElement with JSX IIFE pattern")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
