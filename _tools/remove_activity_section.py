#!/usr/bin/env python3
"""
Remove the 'In the field / Conservation activity.' subsection from the About page.
Keeps the 'Our partners' header + slot 2.8 above it intact.
Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "4b635b80-8097-4e91-be52-33c15e1430e3"  # About bundle

OLD = """        <ImageSlot id="2.8" ratio="7/1"/>
        <div style={{marginTop:56}}>
          <SectionHead kicker="In the field" title="Conservation activity." maxWidth={640}/>
          <ImageSlot id="2.9" ratio="16/7"/>
        </div>
      </div>"""

NEW = """        <ImageSlot id="2.8" ratio="7/1"/>
      </div>"""


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
    if OLD in js:
        js = js.replace(OLD, NEW)
        print("Removed 'In the field / Conservation activity.' subsection")
    elif NEW in js:
        print("Already removed (idempotent no-op)")
    else:
        print("ERROR: target block not found verbatim")
        return
    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
