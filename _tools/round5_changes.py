#!/usr/bin/env python3
"""
Round 5 (June 2026) — Russel's post-review change list.

Image swaps (7) are done by overwriting the existing slot files on disk, so they
need no bundle edit. This script handles the three structural changes:

  1. SLOTS bundle f78573f1: wire slot 6.5 (was kind:'missing') to the new
     sustainability photo Russel supplied.
  2. Eco-Resort "What visitors will do" grid (bundle 23c669aa): hide the
     'Outdoor activities' card.
  3. Nav (bundle 7beb661d): remove the Impact page link (hide Impact page).

Each edit asserts its match count so a rerun fails loudly rather than corrupting.
Decode -> edit -> re-encode each bundle.
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ROOT = HTML_PATH.parent
SLOTS = "f78573f1-64cd-4f59-8544-b39204a866c1"
ECO   = "23c669aa-6716-4ddd-ab28-32729c9c7a83"
NAV   = "7beb661d"  # resolved to full id at runtime

SLOT_65_IMG = "images/Page6/6.5_sustainability.jpg"


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
    m = re.search(r"'" + re.escape(slot_id) + r"'\s*:\s*\{", text)
    if not m:
        return None
    o = m.end() - 1
    depth = 0; in_str = False; q = ''
    i = o
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
                    return o, i
        i += 1
    return None


def set_string_field(body, key, value):
    pat = re.compile(r"(\b" + re.escape(key) + r"\s*:\s*)'(?:\\'|[^'])*'")
    if pat.search(body):
        return pat.sub(lambda m: m.group(1) + js_str(value), body, count=1)
    return body.rstrip().rstrip(",") + ", " + key + ":" + js_str(value)


def sub_once(text, pattern, repl, label, flags=0):
    new, n = re.subn(pattern, repl, text, flags=flags)
    if n != 1:
        raise SystemExit(f"ABORT [{label}]: expected 1 match, found {n}")
    print(f"  ok: {label}")
    return new


def main():
    if not (ROOT / SLOT_65_IMG).exists():
        raise SystemExit(f"ABORT: {SLOT_65_IMG} not on disk")

    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    nav_id = next(k for k in manifest if k.startswith(NAV))

    # ---- 1. SLOTS: wire 6.5 ----
    print("[SLOTS f78573f1] wire 6.5")
    js = decode(manifest[SLOTS])
    span = find_entry_span(js, "6.5")
    if not span:
        raise SystemExit("ABORT: slot 6.5 not found")
    o, c = span
    body = js[o + 1:c]
    if "kind:'missing'" not in body:
        raise SystemExit("ABORT: slot 6.5 is not kind:'missing' (already wired?)")
    body = body.replace("kind:'missing'", "kind:'image'", 1)
    body = set_string_field(body, "real", SLOT_65_IMG)
    body = set_string_field(body, "source", "Website > Final Final Final website photo (Russel, 2026-06-25)")
    js = js[:o + 1] + body + js[c:]
    print("  ok: 6.5 -> kind:image, real set")
    manifest[SLOTS] = encode(js, manifest[SLOTS])

    # ---- 2. ECO: hide 'Outdoor activities' card ----
    print("[ECO 23c669aa] hide Outdoor activities card")
    E = decode(manifest[ECO])
    E = sub_once(
        E,
        r"\['Outdoor activities',\s*'Climbing wall, fishing in designated areas, and guided photography tours\.',\s*null\],\s*",
        "",
        "remove Outdoor activities card",
    )
    if "Outdoor activities" in E:
        raise SystemExit("ABORT: 'Outdoor activities' still present after removal")
    manifest[ECO] = encode(E, manifest[ECO])

    # ---- 3. NAV: remove Impact link ----
    print(f"[NAV {nav_id[:8]}] remove Impact page link")
    N = decode(manifest[nav_id])
    N = sub_once(
        N,
        r"\{\s*k:'impact',\s*label:'Impact'\s*\},\s*",
        "",
        "remove Impact nav item",
    )
    if "k:'impact'" in N:
        raise SystemExit("ABORT: Impact nav item still present")
    manifest[nav_id] = encode(N, manifest[nav_id])

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone — 3 bundles patched, index.html written.")


if __name__ == "__main__":
    main()
