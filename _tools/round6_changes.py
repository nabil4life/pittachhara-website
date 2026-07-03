#!/usr/bin/env python3
"""
Round 6 (2026-06-29) - Nabil's post-review change list (screenshots + notes).

Changes:
  1. SLOTS f78573f1: add slot 10.6 (corporate handshake, already on disk).
  2. Get Involved 23c669aa: point the Corporate partnership tile at 10.6
     (it was reusing 10.5, so two tiles showed the same "10.5" image).
  3. Hide donate: remove the Donate tile on Get Involved (was slot 10.2),
     drop "Five ways" to "Four ways", remove the "Aligned giving levels"
     monthly-giving section; on Home (e1ed9edd) repoint the hero
     "Support our mission" button to Get Involved and remove the bottom
     "Donate now" button. (Nav + floating CTA donate were already hidden.)
  4. Gallery 8.1-8.5 layout: the gallery photos were reusing the partner-logo
     layout (contain, maxHeight 50%, centred) inside a forced 16/6 box, which
     letterboxed single images (8.4) and clipped the 2nd row (8.1-8.3). Add a
     `mosaic` prop that ImageSlot uses ONLY for the Gallery page: cover-filled
     grid with content-driven height. Partner-logo galleries (1.12, 2.8, 4.14)
     and other galleries keep the old layout because they do not pass `mosaic`.

Each edit asserts its match count so a rerun / drift fails loudly.
Note 5.4 (299x168) is NOT touched here: it needs a real high-res original.
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ROOT = HTML_PATH.parent
SLOTS = "f78573f1-64cd-4f59-8544-b39204a866c1"
GI    = "23c669aa-6716-4ddd-ab28-32729c9c7a83"
HOME  = "e1ed9edd-9b1e-42b9-9dfb-20ff24c874fc"
IMG_106 = "images/Page10/10.6_get_involved_new.jpg"


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
        raise SystemExit(f"ABORT [{label}]: expected {n} literal match, found {c}")
    print(f"  ok: {label}")
    return text.replace(old, new)


def rep_re(text, pattern, new, label, n=1, flags=0):
    out, c = re.subn(pattern, new, text, flags=flags)
    if c != n:
        raise SystemExit(f"ABORT [{label}]: expected {n} regex match, found {c}")
    print(f"  ok: {label}")
    return out


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


def main():
    if not (ROOT / IMG_106).exists():
        raise SystemExit(f"ABORT: {IMG_106} not on disk")

    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    # ---------------- 1 + 4: SLOTS bundle (add 10.6, ImageSlot mosaic) ----------------
    print("[SLOTS f78573f1]")
    S = decode(manifest[SLOTS])

    # 1. add 10.6 after 10.5
    if "'10.6'" in S:
        raise SystemExit("ABORT: 10.6 slot already exists")
    span = find_entry_span(S, "10.5")
    if not span:
        raise SystemExit("ABORT: slot 10.5 not found")
    o, c = span
    entry106 = ("'10.6': { kind:'image',   id:'10.6', description:'Corporate partnership: "
                "handshake over financial documents.', source:'Website > Final Final Final website "
                "photo (Russel, 2026-06-25)', real:'" + IMG_106 + "'}")
    S = S[:c + 1] + ",\n  " + entry106 + S[c + 1:]
    print("  ok: added slot 10.6")

    # 4a. mosaic prop on ImageSlot signature
    S = rep(S,
            "const ImageSlot = ({ id, ratio='16/9', compact, chromeless, style, tone='light' }) => {",
            "const ImageSlot = ({ id, ratio='16/9', compact, chromeless, style, tone='light', mosaic }) => {",
            "ImageSlot signature +mosaic")
    # 4b. wrapper aspect ratio: let mosaic size to content
    S = rep(S, "aspectRatio: ratio,", "aspectRatio: mosaic ? 'auto' : ratio,", "wrapper aspectRatio mosaic")
    # 4c. gallery container: grid when mosaic
    S = rep(S,
            "style={{width:'100%', height:'100%', display:'flex', justifyContent:'center', alignItems:'center', gap:'clamp(28px, 4vw, 60px)', padding:'24px 28px', flexWrap:'wrap'}}",
            "style={mosaic ? {width:'100%', display:'grid', gridTemplateColumns: slot.realLogos.length===1?'1fr':'repeat(auto-fill, minmax(clamp(150px, 22vw, 240px), 1fr))', gridAutoRows: slot.realLogos.length===1?'clamp(240px, 42vw, 460px)':'clamp(150px, 20vw, 210px)', gap:4} : {width:'100%', height:'100%', display:'flex', justifyContent:'center', alignItems:'center', gap:'clamp(28px, 4vw, 60px)', padding:'24px 28px', flexWrap:'wrap'}}",
            "gallery container grid when mosaic")
    # 4d. gallery image fill: cover when mosaic
    S = rep(S,
            "style={{maxWidth:'60%', maxHeight:'50%', objectFit:'contain'}}",
            "style={mosaic ? {width:'100%', height:'100%', objectFit:'cover', display:'block'} : {maxWidth:'60%', maxHeight:'50%', objectFit:'contain'}}",
            "gallery image cover when mosaic")
    manifest[SLOTS] = encode(S, manifest[SLOTS])

    # ---------------- 2 + 3 + 4: Get Involved / Gallery bundle ----------------
    print("[GET INVOLVED / GALLERY 23c669aa]")
    G = decode(manifest[GI])

    # 2. corporate tile -> 10.6
    G = rep(G,
            "cta:'Start a conversation', act:'contact', slot:'10.5'",
            "cta:'Start a conversation', act:'contact', slot:'10.6'",
            "corporate tile slot 10.5 -> 10.6")

    # 3a. remove Donate tile from Get Involved tiles array
    G = rep_re(G,
               r"\{ icon:'heart', title:'Donate',[^\n]*?slot:'10\.2' \},\n\s*",
               "",
               "remove Donate tile")
    if "act:'donate'" in G:
        raise SystemExit("ABORT: Donate tile still present after removal")

    # 3b. Five ways -> Four ways
    G = rep(G, "Five ways to support the work", "Four ways to support the work", "Five -> Four ways")

    # 3c. remove the 'Aligned giving levels' monthly-giving section
    anchor = 'SectionHead kicker="Monthly giving" title="Aligned giving levels."'
    ai = G.find(anchor)
    if ai < 0:
        raise SystemExit("ABORT: giving-levels anchor not found")
    sec_start = G.rfind("<section", 0, ai)
    sec_end = G.find("</section>", ai)
    if sec_start < 0 or sec_end < 0:
        raise SystemExit("ABORT: giving-levels section bounds not found")
    sec_end += len("</section>")
    removed = G[sec_start:sec_end]
    if "Aligned giving levels" not in removed or "GIVING_LEVELS" not in removed:
        raise SystemExit("ABORT: giving-levels span looks wrong (safety check failed)")
    if removed.count("<section") != 1:
        raise SystemExit("ABORT: giving-levels span crosses another <section")
    G = G[:sec_start] + G[sec_end:]
    print(f"  ok: removed giving-levels section ({len(removed)} chars)")

    # 4. Gallery page: pass mosaic to the 8.x sections
    G = rep(G,
            '<ImageSlot id={s.slot} ratio="16/6"/>',
            '<ImageSlot id={s.slot} ratio="16/6" mosaic/>',
            "gallery sections +mosaic")
    manifest[GI] = encode(G, manifest[GI])

    # ---------------- 3: Home donate buttons ----------------
    print("[HOME e1ed9edd]")
    H = decode(manifest[HOME])
    # hero "Support our mission" -> Get Involved (no longer a donate trigger)
    H = rep(H,
            '<PillButton variant="clay" onClick={onDonate}>Support our mission',
            '<PillButton variant="clay" onClick={()=>onNav(\'get-involved\')}>Support our mission',
            "home hero button -> get-involved")
    # bottom "Donate now" button removed (keep the Get involved button)
    H = rep_re(H,
               r'\s*<PillButton variant="white" onClick=\{onDonate\}>Donate now <Icon name="arrow" size=\{15\}/></PillButton>',
               "",
               "remove home Donate now button")
    if "Donate now" in H:
        raise SystemExit("ABORT: 'Donate now' still present on Home")
    manifest[HOME] = encode(H, manifest[HOME])

    # ---------------- write ----------------
    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone - bundles patched, index.html written.")


if __name__ == "__main__":
    main()
