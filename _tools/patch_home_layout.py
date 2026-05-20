#!/usr/bin/env python3
"""
Tweak two Home-page ImageSlot ratios:
  - 1.11 Stories from the forest: 16/5 -> 16/7  (taller cards so title text isn't squashed)
  - 1.12 Partner logos: 7/1 -> 5/1            (taller strip so tall logos aren't cropped)

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "e1ed9edd-9b1e-42b9-9dfb-20ff24c874fc"   # Home component

SWAPS = [
    ('<ImageSlot id="1.11" ratio="16/5"/>',  '<ImageSlot id="1.11" ratio="16/7"/>'),
    ('<ImageSlot id="1.12" ratio="7/1"/>',   '<ImageSlot id="1.12" ratio="5/1"/>'),
]


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try: return json.loads(raw), m.start(1), m.end(1)
    except: return json.loads(raw.replace('\\"', '"').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')), m.start(1), m.end(1)


def decode(entry):
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"): raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"): raw = gzip.compress(raw)
    return {"mime": template["mime"], "compressed": template.get("compressed", False), "data": base64.b64encode(raw).decode("ascii")}


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded {BUNDLE_UUID[:8]}: {len(js)} chars")

    for old, new in SWAPS:
        if old in js:
            js = js.replace(old, new)
            print(f"  swapped: {old}  ->  {new}")
        elif new in js:
            print(f"  already patched: {new}")
        else:
            print(f"  NOT FOUND: {old}")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
