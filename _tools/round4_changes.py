#!/usr/bin/env python3
"""
Round 4 (June 2026): remove every "3,465 camera-trap" mention and give the
Research banner a new (number-free) title.

Real occurrences (the matches inside framework bundle 7a50603e are unrelated
timestamps/codepoints and are deliberately left untouched):
  - e1ed9edd : About recognition line
  - 3a22a8a7 : Our Work deep text, a bullet, the banner title, a StatBlock, the
               Confirmed-mammals intro lede (and the stale "Continuous monitoring" stat)
  - 23c669aa : a StatBlock

Each replacement asserts its count so a rerun fails loudly rather than corrupting.
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ABOUT = "e1ed9edd-9b1e-42b9-9dfb-20ff24c874fc"
WORK = "3a22a8a7-725c-47f0-8568-cd5d2c766150"
GALLERY = "23c669aa-6716-4ddd-ab28-32729c9c7a83"


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


def repl(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ABORT [{label}]: expected 1, found {n}")
    print(f"  ok: {label}")
    return text.replace(old, new, 1)


EDITS = {
    ABOUT: [
        ("body:'3,465 camera-trap observations across 18 months, part of the evidence base confirming 17 mammal species across all monitoring methods.'",
         "body:'Eighteen months of camera-trap monitoring, part of the evidence base confirming 17 mammal species across all monitoring methods.'",
         "About recognition line"),
    ],
    WORK: [
        ("documents 3,465 camera trap captures across 18 months, recording 8 confirmed mammal species.",
         "documents an 18-month camera-trap survey recording 8 confirmed mammal species.",
         "Our Work deep text"),
        ("'3,465 camera-trap captures logged and analysed'",
         "'Camera-trap captures logged and analysed'",
         "Our Work bullet"),
        ('Evidence, from <em style={{fontStyle:\'italic\', color:C.gold}}>3,465</em> camera-trap captures.',
         'Evidence, <em style={{fontStyle:\'italic\', color:C.gold}}>frame by frame</em>.',
         "banner title"),
        ('From 3,465 camera-trap observations over 18 months across all monitoring methods.',
         'Documented over 18 months across all monitoring methods.',
         "Confirmed mammals lede"),
        ('number="18 mo" label="Continuous monitoring"',
         'number="18 mo" label="Camera-trap monitoring"',
         "stat: continuous -> camera-trap"),
    ],
    GALLERY: [
        ('<StatBlock number="3,465" label="Camera-trap captures" note="Published in Animals (MDPI, 2024)"/>',
         '<StatBlock number="17" label="Mammal species" note="Confirmed across all monitoring methods"/>',
         "by-the-numbers StatBlock"),
    ],
}


def main():
    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    for bundle, edits in EDITS.items():
        print(f"[{bundle}]")
        t = decode(manifest[bundle])
        for old, new, label in edits:
            t = repl(t, old, new, label)
        manifest[bundle] = encode(t, manifest[bundle])

    # remove the 3,465 StatBlock in WORK (drop the element + trailing whitespace)
    print(f"[{WORK}] remove 3,465 StatBlock")
    t = decode(manifest[WORK])
    t, n = re.subn(r'<StatBlock number="3,465" label="Camera-trap captures"/>\s*', "", t)
    if n != 1:
        raise SystemExit(f"ABORT: WORK 3,465 StatBlock matched {n}")
    print("  ok: removed")
    manifest[WORK] = encode(t, manifest[WORK])

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone — 3 bundles patched.")


if __name__ == "__main__":
    main()
