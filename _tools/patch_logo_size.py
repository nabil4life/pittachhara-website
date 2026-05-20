#!/usr/bin/env python3
"""
Shrink the partner-logo display inside the realLogos gallery render.

Current: maxWidth:90%, maxHeight:80%  (logos fill tile, can look oversized)
New:     maxWidth:65%, maxHeight:55%  (logos sit comfortably with breathing room)
Also widens the grid container padding from 18px 22px to 24px 28px.

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"   # holds ImageSlot

SWAPS = [
    # Resize logos to whatever the latest target is.
    # Last attempt was 50/40 (too small). Bumping to 60/50 as middle ground.
    ("maxWidth:'90%', maxHeight:'80%', objectFit:'contain'",
     "maxWidth:'60%', maxHeight:'50%', objectFit:'contain'"),
    ("maxWidth:'65%', maxHeight:'55%', objectFit:'contain'",
     "maxWidth:'60%', maxHeight:'50%', objectFit:'contain'"),
    ("maxWidth:'50%', maxHeight:'40%', objectFit:'contain'",
     "maxWidth:'60%', maxHeight:'50%', objectFit:'contain'"),
    # Container padding — keep the gap and padding we last set
    ("gap:14, padding:'18px 22px'",
     "gap:22, padding:'30px 34px'"),
    ("gap:18, padding:'24px 28px'",
     "gap:22, padding:'30px 34px'"),
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


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    for old, new in SWAPS:
        if old in js:
            js = js.replace(old, new)
            print(f"  swapped:  {old[:60]}...")
        elif new in js:
            print(f"  already patched")
        else:
            print(f"  NOT FOUND: {old[:60]}...")
    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
