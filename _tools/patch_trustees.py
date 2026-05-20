#!/usr/bin/env python3
"""
Page 2 quirk fix: each trustee card was rendering all 13 trustee photos because
the About React component reused <ImageSlot id="2.3"/> inside trustee.map().

This patch:
  1. Adds `photo:` to each TRUSTEES array entry (matched best-effort by name).
  2. Replaces the per-card <ImageSlot id="2.3" .../> with <img src={t.photo}.../>.
  3. Also removes the now-redundant slot 2.3 realLogos so the gallery render
     doesn't appear twice (handled inside enrich_slots.py — we leave 2.3 alone
     here in case it's wanted as a header gallery; if not, set 2.3 to nothing).

Idempotent: re-running detects the prior patch via the `photo:` keys and skips.

Trustee→file mapping is BEST-EFFORT and needs Russel to verify the actual
person→photo mapping.
"""
import re, json, base64, gzip, shutil
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BACKUP_PATH = Path(__file__).parent.parent / "index.original.html"
ABOUT_BUNDLE_UUID = "4b635b80-8097-4e91-be52-33c15e1430e3"

# Best-effort name → filename slug mapping. Slugs not in this list go to ambiguous file.
NAME_TO_SLUG = {
    "Mahfuz Ahmed Russel":       "russel",
    "Shafiq Quais Hassan":       "quais",
    "Sanjida Sharmin (Jui)":     "jui",
    "Dr Sayam U. Chowdhury":     "extra",      # AMBIGUOUS — verify with Russel
    "Sharier Khan":              "sharier",
    "A.R.M. Qayyum Khan":        "qayyum",
    "Dr Rafia Nazneen":          "rafia",
    "Md. Mahbubur Rahman":       "rony",       # AMBIGUOUS — verify with Russel
    "Shah Md Imtiaz Noor Sadi":  "sadi",
    "Joyanto Sen":               "joyanta",
    "Ar. Abu Musa Iftekhar":     "musa",
    "Ar. Shahidullah Faruq":     "faruq",
    "Md. Jahidul Kabir":         "unknown",    # AMBIGUOUS — verify with Russel
}


def js_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def find_extension_for_slug(slug: str) -> str:
    """Look up the actual file in images/Page2/ for a given trustee slug."""
    folder = Path(__file__).parent.parent / "images" / "Page2"
    matches = sorted(folder.glob(f"2.3_trustee_{slug}.*"))
    if not matches:
        return ""
    return matches[0].name  # e.g. "2.3_trustee_russel.jpg"


def load_manifest(html: str):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try:
        manifest = json.loads(raw)
    except Exception:
        raw_un = raw.replace('\\"', '"').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
        manifest = json.loads(raw_un)
    return manifest, m.start(1), m.end(1)


def decode_entry(entry):
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode_entry(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"):
        raw = gzip.compress(raw)
    return {
        "mime": template["mime"],
        "compressed": template.get("compressed", False),
        "data": base64.b64encode(raw).decode("ascii"),
    }


def patch_trustees_array(js: str) -> tuple:
    """For each TRUSTEES entry, append `, photo:'images/Page2/2.3_trustee_X.jpg'`."""
    changed = 0
    skipped = 0
    out = js
    for name, slug in NAME_TO_SLUG.items():
        # Find the entry: { name:'<exact name>', ... }
        # Escape name for regex; quotes inside name (parens etc.) are fine
        # match the opening {  followed by name:'...' up to next matching }
        # Use depth-balanced approach
        name_pat = re.compile(r"\{[^{}]*name:'" + re.escape(name) + r"'[^{}]*\}")
        m = name_pat.search(out)
        if not m:
            print(f"  skip (entry not found): {name}")
            skipped += 1
            continue
        entry = m.group(0)
        if "photo:" in entry:
            # Idempotent — already patched
            skipped += 1
            continue
        filename = find_extension_for_slug(slug)
        if not filename:
            print(f"  skip (no file for slug '{slug}'): {name}")
            skipped += 1
            continue
        photo_path = f"images/Page2/{filename}"
        # Insert before the closing brace
        new_entry = entry[:-1].rstrip() + ", photo:" + js_str(photo_path) + " }"
        out = out[:m.start()] + new_entry + out[m.end():]
        changed += 1
    return out, changed, skipped


def patch_trustee_card(js: str) -> int:
    """Replace <ImageSlot id="2.3" ratio="1/1" compact/> inside TrusteeCard with conditional img."""
    target = '<ImageSlot id="2.3" ratio="1/1" compact/>'
    if target not in js:
        # Maybe already patched
        if "t.photo" in js:
            return 0  # idempotent
        print(f"  NOTICE: target ImageSlot id=2.3 with ratio=1/1 not found verbatim")
        return -1
    # JSX replacement: conditional render
    replacement = (
        '{t.photo'
        ' ? <img src={t.photo} alt={t.name} loading="lazy"'
        '       style={{width:"100%", aspectRatio:"1/1", objectFit:"cover", borderRadius:8, display:"block"}}/>'
        ' : <ImageSlot id="2.3" ratio="1/1" compact/>}'
    )
    return js.replace(target, replacement).count(target) * 0 or 1, js.replace(target, replacement)


def main():
    if not BACKUP_PATH.exists():
        shutil.copy2(HTML_PATH, BACKUP_PATH)
        print(f"Backup created: {BACKUP_PATH}")
    html = HTML_PATH.read_text()
    manifest, m_start, m_end = load_manifest(html)
    entry = manifest[ABOUT_BUNDLE_UUID]
    js = decode_entry(entry)
    print(f"Decoded About bundle: {len(js)} chars")

    js, n_changed, n_skipped = patch_trustees_array(js)
    print(f"TRUSTEES entries: {n_changed} added photo, {n_skipped} skipped")

    result = patch_trustee_card(js)
    if isinstance(result, tuple):
        n_card, js = result
        print(f"TrusteeCard ImageSlot replaced: {n_card}")
    else:
        print(f"TrusteeCard already patched (or target missing)")

    # Re-encode
    manifest[ABOUT_BUNDLE_UUID] = encode_entry(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:m_start] + "\n" + new_json + html[m_end:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")
    print(f"Wrote: {HTML_PATH}")


if __name__ == "__main__":
    main()
