#!/usr/bin/env python3
"""
Page 3 fixes:
  1. Decouple the hero from the Forest Conservation card. The Work component used
     <ImageSlot id="3.1" ratio="21/7" chromeless/> for the hero AND id={p.slot}
     (=3.1) for the programme card. Rename the hero slot to '3.1hero' so the two
     can differ. Add SLOTS['3.1hero'] = video; revert SLOTS['3.1'] to the still image.
  2. Set SLOTS['3.5'] (Community Library) back to MISSING — remove the stand-in real
     so it shows the red MISSING placeholder (Russel to supply).
  (3.7 nursery is already MISSING — no change needed.)

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
SLOTS_BUNDLE = "f78573f1-64cd-4f59-8544-b39204a866c1"
WORK_BUNDLE = "3a22a8a7-725c-47f0-8568-cd5d2c766150"


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


def strip_keys(entry, keys):
    for k in keys:
        entry = re.sub(r",\s*" + k + r":(?:'(?:\\'|[^'])*'|\[[^\]]*\])", "", entry)
    return entry


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)

    # ---- 1a. Work bundle: rename hero ImageSlot id 3.1 -> 3.1hero ----
    work = manifest[WORK_BUNDLE]
    wjs = decode(work)
    hero_old = '<ImageSlot id="3.1" ratio="21/7" tone="dark" style={{height:\'100%\'}} chromeless/>'
    hero_new = '<ImageSlot id="3.1hero" ratio="21/7" tone="dark" style={{height:\'100%\'}} chromeless/>'
    if hero_old in wjs:
        wjs = wjs.replace(hero_old, hero_new)
        manifest[WORK_BUNDLE] = encode(wjs, work)
        print("Work hero ImageSlot id 3.1 -> 3.1hero")
    elif hero_new in wjs:
        print("Work hero already renamed")
    else:
        print("WARN: hero ImageSlot not found verbatim in Work bundle")

    # ---- 1b/2. SLOTS bundle edits ----
    sb = manifest[SLOTS_BUNDLE]
    sjs = decode(sb)

    # Revert SLOTS['3.1'] real to the still image (card)
    m = re.search(r"'3\.1'\s*:\s*\{[^{}]*\}", sjs)
    if m:
        entry = strip_keys(m.group(0), ["real"])
        entry = entry[:-1].rstrip() + ", real:" + js_str("images/Page3/3.1_forest_conservation.jpg") + " }"
        sjs = sjs[:m.start()] + entry + sjs[m.end():]
        print("SLOTS['3.1'] reverted to still image")

    # Add SLOTS['3.1hero'] if not present — insert right after SLOTS['3.1'] entry
    if "'3.1hero'" not in sjs:
        m = re.search(r"'3\.1'\s*:\s*\{[^{}]*\},", sjs)
        if m:
            hero_entry = (" '3.1hero': { kind:'video', id:'3.1hero', "
                          "description:'Our Work hero — drone over the protected forest.', "
                          "source:'Drone & Camera shooting', "
                          "real:" + js_str("images/Page3/3.1_hero_drone_video.mp4") + " },")
            sjs = sjs[:m.end()] + hero_entry + sjs[m.end():]
            print("SLOTS['3.1hero'] added (video)")
    else:
        print("SLOTS['3.1hero'] already present")

    # Set SLOTS['3.5'] to MISSING — strip real, set kind:'missing'
    m = re.search(r"'3\.5'\s*:\s*\{[^{}]*\}", sjs)
    if m:
        entry = strip_keys(m.group(0), ["real", "standIn"])
        # flip kind to 'missing'
        entry = re.sub(r"kind:'[^']*'", "kind:'missing'", entry, count=1)
        sjs = sjs[:m.start()] + entry + sjs[m.end():]
        print("SLOTS['3.5'] set to MISSING (stand-in removed)")

    manifest[SLOTS_BUNDLE] = encode(sjs, sb)

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
