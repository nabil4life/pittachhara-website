#!/usr/bin/env python3
"""
Fix slots whose image exists on disk but does not render on the live site.

Two failure modes found by the June 2026 audit:
  A. Slot still marked kind:'missing' (never wired) although Russel supplied the photo.
  B. Slot has real:'<path>' pointing at a filename that no longer exists
     (species rename black_rat->squirrel, wrong .jpg/.png extension, or the
     original design's assets/page1/* paths that were never shipped).

This script edits the SLOTS object inside bundle f78573f1 (decode -> patch -> re-encode).
It is idempotent: re-running with the same inputs yields the same file.

Sayam portrait is handled separately (file overwrite, no bundle edit needed).
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ROOT = HTML_PATH.parent
SLOTS_BUNDLE = "f78573f1-64cd-4f59-8544-b39204a866c1"

# slot -> real path (single image). Also flips kind:'missing' -> kind:'image'.
IMAGE_FIXES = {
    "1.2": "images/Page1/1.2_forest_conservation_card.jpg",
    "1.3": "images/Page1/1.3_wildlife_research_card.jpg",
    "1.4": "images/Page1/1.4_free_healthcare_card.jpg",
    "1.6": "images/Page1/1.6_womens_empowerment_card.jpg",
    "1.7": "images/Page1/1.7_wildlife_rescue_card.jpg",
    "1.9": "images/Page1/1.9_balipara_award.jpg",
    "3.7": "images/Page3/3.7_nursery.jpg",
    "4.5": "images/Page4/4.5_indian_civet.png",
    "4.9": "images/Page4/4.9_squirrel.jpg",
    "5.2": "images/Page5/5.2_regeneration.png",
    "5.3": "images/Page5/5.3_agroforestry.jpg",
    "5.4": "images/Page5/5.4_corridor.jpg",
}

# slot -> list of (src, alt). Sets realLogos and flips kind:'missing' -> kind:'gallery'.
GALLERY_FIXES = {
    "4.10": [("images/Page4/4.10_birds.jpg", "Birds")],
    "4.11": [("images/Page4/4.11_reptiles.jpg", "Reptiles & Amphibians")],
    "8.4":  [("images/Page8/8.4_01.jpg", "Nursery & Restoration")],
}


def decode(e):
    r = base64.b64decode(e["data"])
    if e.get("compressed"):
        r = gzip.decompress(r)
    return r.decode("utf-8")


def encode(text, tpl):
    raw = text.encode("utf-8")
    if tpl.get("compressed"):
        raw = gzip.compress(raw)
    return {"mime": tpl["mime"], "compressed": tpl.get("compressed", False),
            "data": base64.b64encode(raw).decode("ascii")}


def js_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def find_entry_span(text, slot_id):
    """Return (open_brace_idx, close_brace_idx) for 'slot_id': { ... }, brace-balanced."""
    m = re.search(r"'" + re.escape(slot_id) + r"'\s*:\s*\{", text)
    if not m:
        return None
    open_idx = m.end() - 1
    depth = 0
    in_str = False
    quote = ''
    i = open_idx
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True; quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return open_idx, i
        i += 1
    return None


def set_string_field(body, key, value):
    """Replace key:'...' inside body, or insert it before the closing brace content end."""
    pat = re.compile(r"(\b" + re.escape(key) + r"\s*:\s*)'(?:\\'|[^'])*'")
    if pat.search(body):
        return pat.sub(lambda m: m.group(1) + js_str(value), body, count=1)
    return body.rstrip().rstrip(",") + ", " + key + ":" + js_str(value)


def set_array_field(body, key, literal):
    """Replace key:[...] inside body, or insert it. literal is a ready JS array string."""
    pat = re.compile(r"\b" + re.escape(key) + r"\s*:\s*\[[^\]]*\]")
    if pat.search(body):
        return pat.sub(key + ":" + literal, body, count=1)
    return body.rstrip().rstrip(",") + ", " + key + ":" + literal


def logos_literal(pairs):
    return "[" + ", ".join("{src:" + js_str(s) + ", alt:" + js_str(a) + "}" for s, a in pairs) + "]"


def patch_slot(js, slot_id, *, kind=None, real=None, logos=None):
    span = find_entry_span(js, slot_id)
    if not span:
        print(f"  WARN slot {slot_id} not found"); return js
    o, c = span
    body = js[o + 1:c]
    before = body
    if kind:
        body = re.sub(r"kind\s*:\s*'missing'", "kind:'" + kind + "'", body, count=1)
    if real is not None:
        body = set_string_field(body, "real", real)
    if logos is not None:
        body = set_array_field(body, "realLogos", logos_literal(logos))
    if body != before:
        print(f"  {slot_id}: patched")
    else:
        print(f"  {slot_id}: no change (already correct)")
    return js[:o + 1] + body + js[c:]


def main():
    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)
    entry = manifest[SLOTS_BUNDLE]
    js = decode(entry)

    # Safety: every target file must exist on disk before we wire it.
    missing = []
    for sid, p in IMAGE_FIXES.items():
        if not (ROOT / p).exists():
            missing.append(p)
    for sid, pairs in GALLERY_FIXES.items():
        for s, _ in pairs:
            if not (ROOT / s).exists():
                missing.append(s)
    if missing:
        raise SystemExit("ABORT — target files missing on disk:\n  " + "\n  ".join(missing))

    print("=== image slots ===")
    for sid, path in IMAGE_FIXES.items():
        js = patch_slot(js, sid, kind="image", real=path)
    print("=== gallery slots ===")
    for sid, pairs in GALLERY_FIXES.items():
        js = patch_slot(js, sid, kind="gallery", logos=pairs)

    manifest[SLOTS_BUNDLE] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone — bundle re-encoded and written.")


if __name__ == "__main__":
    main()
