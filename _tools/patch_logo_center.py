#!/usr/bin/env python3
"""
Switch the realLogos container from a stretched grid to a centered flexbox.
With grid + repeat(4, 1fr), logos spread across full width with empty space inside each cell.
With flex + justifyContent:center, logos cluster in the middle of the strip.
Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

# The container div opening as it currently stands (after the prior patches).
# We tolerate any gap/padding values since they've been mutated.
OLD = re.compile(
    r"<div style=\{\{width:'100%', height:'100%', display:'grid', "
    r"gridTemplateColumns:`repeat\(\$\{Math\.min\(slot\.realLogos\.length, 4\)\}, 1fr\)`, "
    r"gap:\d+, padding:'[^']+', "
    r"alignItems:'center', justifyItems:'center'\}\}>"
)

NEW = (
    "<div style={{width:'100%', height:'100%', display:'flex', "
    "justifyContent:'center', alignItems:'center', "
    "gap:'clamp(28px, 4vw, 60px)', padding:'24px 28px', flexWrap:'wrap'}}>"
)


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

    if NEW in js:
        print("Already converted to centered flex layout")
        return
    m = OLD.search(js)
    if not m:
        print("Container pattern not found")
        return
    js = js[:m.start()] + NEW + js[m.end():]
    print("Container swapped from grid to centered flex")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
