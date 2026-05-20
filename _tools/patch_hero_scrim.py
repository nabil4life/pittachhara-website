#!/usr/bin/env python3
"""
Add a green scrim (forest #17362A gradient) over the Page 3 'Our Work' hero video
so the white headline + body text read clearly against bright drone footage.
The scrim sits between the video and the text, so no text colours change.
Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
WORK_BUNDLE = "3a22a8a7-725c-47f0-8568-cd5d2c766150"

ANCHOR = """          <ImageSlot id="3.1hero" ratio="21/7" tone="dark" style={{height:'100%'}} chromeless/>
        </div>"""

SCRIM = """          <ImageSlot id="3.1hero" ratio="21/7" tone="dark" style={{height:'100%'}} chromeless/>
        </div>
        <div style={{position:'absolute', inset:'12px', borderRadius:12, background:'linear-gradient(90deg, rgba(23,54,42,0.90) 0%, rgba(23,54,42,0.66) 52%, rgba(23,54,42,0.40) 100%)', pointerEvents:'none'}}/>"""


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
    entry = manifest[WORK_BUNDLE]
    js = decode(entry)
    if "rgba(23,54,42,0.90)" in js:
        print("Scrim already present")
        return
    if ANCHOR not in js:
        print("ERROR: hero anchor not found")
        return
    js = js.replace(ANCHOR, SCRIM, 1)
    manifest[WORK_BUNDLE] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Green scrim added over Page 3 hero")


if __name__ == "__main__":
    main()
