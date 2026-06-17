#!/usr/bin/env python3
"""
Round 2 (June 2026) site changes:

  1. Populate blank galleries 8.1 / 8.2 / 8.3 / 8.5 from images/Page8/8.X_* (realLogos was []).
  2. Wire Research slot 4.13 to reuse the 2.5 MDPI cover, and link it to the new paper PDF.
  3. Our Work page (bundle 3a22a8a7): 16.76 -> 30 hectares; "eight mammal species" -> "17 mammal species".
  4. Our Work page: give "Read on MDPI" + "Download PDF" buttons a real href to the paper PDF.
  5. Gallery page (bundle 23c669aa): "Eight+ confirmed mammal species" -> "17 confirmed mammal species".

Idempotent where practical (string replacements assert their expected counts so a second
run fails loudly rather than corrupting). Decode -> edit -> re-encode each bundle.
"""
import re, json, gzip, base64, glob
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ROOT = HTML_PATH.parent
SLOTS = "f78573f1-64cd-4f59-8544-b39204a866c1"
WORK = "3a22a8a7-725c-47f0-8568-cd5d2c766150"
GALLERY = "23c669aa-6716-4ddd-ab28-32729c9c7a83"

PAPER_PDF = "images/Page4/4.13_mammals_paper.pdf"
COVER = "images/Page2/2.5_mdpi_cover.jpg"

GALLERY_THEMES = {
    "8.1": "Wildlife and camera traps",
    "8.2": "The forest",
    "8.3": "Community programmes",
    "8.5": "Wildlife rescue and rehabilitation",
}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ABORT [{label}]: expected exactly 1 occurrence of {old!r}, found {n}")
    print(f"  ok: {label}")
    return text.replace(old, new, 1)


def find_entry_span(text, slot_id):
    m = re.search(r"'" + re.escape(slot_id) + r"'\s*:\s*\{", text)
    if not m:
        return None
    open_idx = m.end() - 1
    depth = 0; in_str = False; q = ''
    i = open_idx
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '\\':
                i += 2; continue
            if ch == q:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True; q = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return open_idx, i
        i += 1
    return None


def set_string_field(body, key, value):
    pat = re.compile(r"(\b" + re.escape(key) + r"\s*:\s*)'(?:\\'|[^'])*'")
    if pat.search(body):
        return pat.sub(lambda m: m.group(1) + js_str(value), body, count=1)
    return body.rstrip().rstrip(",") + ", " + key + ":" + js_str(value)


def set_array_field(body, key, literal):
    pat = re.compile(r"\b" + re.escape(key) + r"\s*:\s*\[[^\]]*\]")
    if pat.search(body):
        return pat.sub(key + ":" + literal, body, count=1)
    return body.rstrip().rstrip(",") + ", " + key + ":" + literal


def patch_slot_body(js, slot_id, fn):
    span = find_entry_span(js, slot_id)
    if not span:
        raise SystemExit(f"ABORT: slot {slot_id} not found")
    o, c = span
    return js[:o + 1] + fn(js[o + 1:c]) + js[c:]


def gallery_logos(slot_id):
    files = sorted(p for p in glob.glob(str(ROOT / f"images/Page8/{slot_id}_*"))
                   if Path(p).suffix.lower() in IMG_EXT)
    theme = GALLERY_THEMES[slot_id]
    pairs = []
    total = 0
    for i, p in enumerate(files, 1):
        rel = str(Path(p).relative_to(ROOT))
        pairs.append((rel, f"{theme} {i:02d}"))
        total += Path(p).stat().st_size
    lit = "[" + ", ".join("{src:" + js_str(s) + ", alt:" + js_str(a) + "}" for s, a in pairs) + "]"
    print(f"  {slot_id}: {len(pairs)} images ({total/1024/1024:.1f} MB total)")
    return lit


def main():
    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    # safety: paper PDF + cover must exist
    for p in (PAPER_PDF, COVER):
        if not (ROOT / p).exists():
            raise SystemExit(f"ABORT: missing required file {p}")

    # ---- bundle f78573f1: galleries + 4.13 ----
    print("[SLOTS f78573f1]")
    js = decode(manifest[SLOTS])
    for sid in ("8.1", "8.2", "8.3", "8.5"):
        lit = gallery_logos(sid)
        js = patch_slot_body(js, sid, lambda b, L=lit: set_array_field(b, "realLogos", L))
    js = patch_slot_body(js, "4.13", lambda b: set_string_field(set_string_field(b, "real", COVER), "link", PAPER_PDF))
    print("  4.13: real -> 2.5 cover, link -> paper PDF")
    manifest[SLOTS] = encode(js, manifest[SLOTS])

    # ---- bundle 3a22a8a7: Our Work stats + paper buttons ----
    print("[WORK 3a22a8a7]")
    W = decode(manifest[WORK])
    W = replace_once(W, "16.76", "30", "16.76 -> 30 hectares")
    W = replace_once(W, "home to eight mammal species", "home to 17 mammal species", "eight -> 17 mammal species (glance)")
    W = replace_once(W,
        '<PillButton variant="forest">Read on MDPI ',
        '<PillButton variant="forest" href="' + PAPER_PDF + '" target="_blank" rel="noopener noreferrer">Read on MDPI ',
        "Read on MDPI -> PDF link")
    W = replace_once(W,
        '<PillButton variant="forestOut">Download PDF ',
        '<PillButton variant="forestOut" href="' + PAPER_PDF + '" download="Pittachhara_Mammals_Assessment_2024.pdf">Download PDF ',
        "Download PDF -> PDF link")
    manifest[WORK] = encode(W, manifest[WORK])

    # ---- bundle 23c669aa: gallery header mammal count ----
    print("[GALLERY 23c669aa]")
    G = decode(manifest[GALLERY])
    G = replace_once(G, "Eight+ confirmed mammal species", "17 confirmed mammal species", "gallery header eight -> 17")
    manifest[GALLERY] = encode(G, manifest[GALLERY])

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone — 3 bundles patched, index.html written.")


if __name__ == "__main__":
    main()
