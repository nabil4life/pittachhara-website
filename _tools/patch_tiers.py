#!/usr/bin/env python3
"""
Page 11 quirk fix: each tier card on Donate page was rendering all 6 tier photos
because the component uses <ImageSlot id={g.slot}/> inside GIVING_LEVELS.map() and
every level has slot:'11.2', so all 6 cards rendered the 6-image gallery (36 imgs).

This patch:
  1. Adds `image:` to each GIVING_LEVELS entry, mapped by label keyword to the
     matching tier file in images/Page11/.
  2. Replaces the per-card <ImageSlot id={g.slot} ratio="4/3" compact/> with
     <img src={g.image} alt={g.label} .../>.

Idempotent.
"""
import re, json, base64, gzip, shutil
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "23c669aa-6716-4ddd-ab28-32729c9c7a83"  # Gallery/Donate/Contact/etc bundle

LABEL_TO_FILE = {
    "Seed Protector":      "images/Page11/11.2_tier_seed.jpg",
    "Healthcare Supporter":"images/Page11/11.2_tier_healthcare.jpg",
    "Forest Guardian":     "images/Page11/11.2_tier_forest.jpg",
    "Education Champion":  "images/Page11/11.2_tier_education.jpg",
    "Wildlife Protector":  "images/Page11/11.2_tier_wildlife.jpg",
    "Ecosystem Patron":    "images/Page11/11.2_tier_ecosystem.jpg",
}


def js_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try:
        manifest = json.loads(raw)
    except Exception:
        manifest = json.loads(raw.replace('\\"', '"').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<'))
    return manifest, m.start(1), m.end(1)


def decode(entry):
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"):
        raw = gzip.compress(raw)
    return {
        "mime": template["mime"],
        "compressed": template.get("compressed", False),
        "data": base64.b64encode(raw).decode("ascii"),
    }


def patch_levels(js: str):
    changed = 0
    out = js
    for label, path in LABEL_TO_FILE.items():
        pat = re.compile(r"\{[^{}]*label:'" + re.escape(label) + r"'[^{}]*\}")
        m = pat.search(out)
        if not m:
            print(f"  skip (entry not found): {label}")
            continue
        entry = m.group(0)
        if "image:" in entry:
            continue  # idempotent
        new_entry = entry[:-1].rstrip() + ", image:" + js_str(path) + " }"
        out = out[:m.start()] + new_entry + out[m.end():]
        changed += 1
    return out, changed


def patch_tier_card(js: str):
    target = '<ImageSlot id={g.slot} ratio="4/3" compact/>'
    if target not in js:
        if "g.image" in js:
            return js, 0  # idempotent
        return js, -1
    replacement = (
        '{g.image'
        ' ? <img src={g.image} alt={g.label} loading="lazy"'
        '       style={{width:"100%", aspectRatio:"4/3", objectFit:"cover", borderRadius:8, display:"block"}}/>'
        ' : <ImageSlot id={g.slot} ratio="4/3" compact/>}'
    )
    return js.replace(target, replacement), 1


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded bundle {BUNDLE_UUID[:8]}: {len(js)} chars")

    js, n_levels = patch_levels(js)
    print(f"GIVING_LEVELS image: added to {n_levels} entries")

    js, n_card = patch_tier_card(js)
    print(f"Tier card ImageSlot replaced: {n_card}")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
