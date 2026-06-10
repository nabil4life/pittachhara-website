#!/usr/bin/env python3
"""
Russel-driven SLOT metadata changes from his 6 June 2026 email:

  - Slot 4.9 species swap: Black Rat -> Orange-bellied Himalayan Squirrel
    (description, section title, source folder)
  - Slots 6.2 and 6.3 transition from MISSING to filled (architect renders provided)
    — flip kind from 'missing' back to 'image'.

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
SLOTS_BUNDLE = "f78573f1-64cd-4f59-8544-b39204a866c1"


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


def js_str(s): return "'" + s.replace("\\","\\\\").replace("'","\\'") + "'"


def update_slot_field(sjs, slot_id, key, new_value):
    """Find SLOTS[slot_id] entry and update or insert key:'new_value' (string literal)."""
    pat = re.compile(r"'" + re.escape(slot_id) + r"'\s*:\s*\{([^{}]*(?:\[[^\]]*\][^{}]*)*)\}")
    m = pat.search(sjs)
    if not m:
        print(f"  WARN: slot {slot_id} not found")
        return sjs
    body = m.group(1)
    # Replace existing key:'...' or insert before closing brace
    key_pat = re.compile(r"(\b" + re.escape(key) + r"\s*:\s*)'(?:\\'|[^'])*'")
    if key_pat.search(body):
        new_body = key_pat.sub(lambda mm: mm.group(1) + js_str(new_value), body)
    else:
        new_body = body.rstrip().rstrip(",") + ", " + key + ":" + js_str(new_value)
    return sjs[:m.start()] + "'" + slot_id + "': {" + new_body + "}" + sjs[m.end():]


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[SLOTS_BUNDLE]
    js = decode(entry)

    # 1. 4.9 species swap — update description + section
    js = update_slot_field(js, "4.9",
        "description",
        "Camera-trap or rescue frame of the Orange-bellied Himalayan Squirrel (replaces Black Rat per Russel, June 2026).")
    print("4.9 description updated: Black Rat -> Orange-bellied Himalayan Squirrel")

    # 2. 6.2, 6.3, and 3.5 transition from 'missing' to 'image' (Russel supplied)
    for sid in ("6.2", "6.3", "3.5"):
        pat = re.compile(r"'" + re.escape(sid) + r"'\s*:\s*\{([^{}]*)\}")
        m = pat.search(js)
        if m:
            new_body = re.sub(r"kind:'missing'", "kind:'image'", m.group(1), count=1)
            js = js[:m.start()] + "'" + sid + "': {" + new_body + "}" + js[m.end():]
            print(f"{sid} kind flipped: missing -> image")
        else:
            print(f"  WARN: {sid} not found")

    manifest[SLOTS_BUNDLE] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
