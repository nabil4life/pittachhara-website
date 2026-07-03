#!/usr/bin/env python3
"""
Round 7 (2026-07-03) - gallery click-to-zoom + drop one image.

All edits are in the SLOTS bundle f78573f1 (holds the ImageSlot component and
the slot registry).

  1. Click-to-zoom lightbox for gallery (mosaic) images:
     - mosaic image style gains cursor:'zoom-in'
     - mosaic image gains an onClick that opens a full-image overlay
       (click anywhere or press Escape to close). Vanilla DOM, no React
       state/hooks, so it is independent of how React is scoped in this bundle.
     Non-mosaic images (partner logos etc.) get onClick=undefined, so they are
     unaffected.
  2. Remove "Wildlife and camera traps 11" (images/Page8/8.1_11.jpg) from the
     8.1 gallery set (it duplicated 8.1_10). The file is left on disk, just
     no longer referenced.

Assert-counted so drift fails loudly.
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
SLOTS = "f78573f1-64cd-4f59-8544-b39204a866c1"

ONCLICK = (
    " onClick={mosaic ? (e)=>{"
    " const o=document.createElement('div');"
    " o.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.92);"
    "display:flex;align-items:center;justify-content:center;z-index:99999;"
    "cursor:zoom-out;padding:4vw';"
    " const im=document.createElement('img');"
    " im.src=l.src;"
    " im.style.cssText='max-width:96vw;max-height:92vh;object-fit:contain;"
    "border-radius:8px;box-shadow:0 12px 48px rgba(0,0,0,0.55)';"
    " o.appendChild(im);"
    " o.addEventListener('click',()=>o.remove());"
    " document.addEventListener('keydown',function k(ev){"
    " if(ev.key==='Escape'){ o.remove(); document.removeEventListener('keydown',k); } });"
    " document.body.appendChild(o);"
    " } : undefined}"
)


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


def rep(text, old, new, label, n=1):
    c = text.count(old)
    if c != n:
        raise SystemExit(f"ABORT [{label}]: expected {n} match, found {c}")
    print(f"  ok: {label}")
    return text.replace(old, new)


def main():
    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    print("[SLOTS f78573f1]")
    S = decode(manifest[SLOTS])

    # 1a. cursor on mosaic image
    S = rep(S,
            "{mosaic ? {width:'100%', height:'100%', objectFit:'cover', display:'block'} : {maxWidth:'60%', maxHeight:'50%', objectFit:'contain'}}",
            "{mosaic ? {width:'100%', height:'100%', objectFit:'cover', display:'block', cursor:'zoom-in'} : {maxWidth:'60%', maxHeight:'50%', objectFit:'contain'}}",
            "mosaic image cursor:zoom-in")

    # 1b. onClick zoom on the gallery/logos image (fires only when mosaic)
    if S.count("title={l.alt}") != 1:
        raise SystemExit(f"ABORT: expected 1 'title={{l.alt}}', found {S.count('title={l.alt}')}")
    S = rep(S, "title={l.alt}", "title={l.alt}" + ONCLICK, "gallery image onClick zoom")

    # 2. drop 8.1_11 (Wildlife and camera traps 11)
    S = rep(S,
            "{src:'images/Page8/8.1_11.jpg', alt:'Wildlife and camera traps 11'}, ",
            "",
            "remove 8.1_11 (Wildlife and camera traps 11)")
    if "8.1_11.jpg" in S:
        raise SystemExit("ABORT: 8.1_11 still referenced after removal")

    manifest[SLOTS] = encode(S, manifest[SLOTS])
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone - SLOTS bundle patched, index.html written.")


if __name__ == "__main__":
    main()
