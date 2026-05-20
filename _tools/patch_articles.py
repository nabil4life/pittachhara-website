#!/usr/bin/env python3
"""
Two-part patch for the Stories from the forest section (slot 1.11):

  1. In the f78573f1 bundle: expand the hasArticles render so each card shows
     hero image (if a.image is set) + host kicker + title + excerpt (if a.excerpt set).
  2. In the same bundle's SLOTS['1.11'].articles array: add `image` and `excerpt`
     fields to each of the 3 entries.

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

# Article enrichments — image is best-effort from existing on-disk photos
ARTICLES = {
    # by URL prefix
    "tbsnews.net": {
        "image":   "images/Page1/1.9_balipara_award.jpg",
        "excerpt": "Inside Khagrachhari's largest fair celebrating primate conservation — villagers, scientists and indigenous communities gathered around one of the country's last semi-evergreen hill forests.",
    },
    "theclimatewatch.com": {
        "image":   "images/Page1/1.10_founder_russel_v2.jpg",
        "excerpt": "Mahfuz Russel leads a grassroots effort to protect wildlife and restore forests in Khagrachhari, taking on deforestation, fires and poaching one hill at a time.",
    },
    "facebook.com": {
        "image":   "images/Page1/1.2_forest_conservation_card.jpg",
        "excerpt": "Ongoing field reports from Pittachhara's monitoring teams — rescues, restoration, community programmes and seasonal wildlife sightings, posted live from the forest.",
    },
}

# --- render block swap (current → new) ----------------------------------------

OLD_RENDER = """hasArticles && (
          <div style={{width:'100%', height:'100%', display:'grid', gridTemplateColumns:`repeat(${slot.articles.length}, 1fr)`, gap:0}}>
            {slot.articles.map(a => (
              <a key={a.url} href={a.url} target="_blank" rel="noopener noreferrer" style={{
                display:'flex', flexDirection:'column', justifyContent:'space-between',
                padding:'14px 16px',
                background:`linear-gradient(135deg, ${a.tint||'rgba(46,90,72,0.10)'} 0%, rgba(46,90,72,0.18) 100%)`,
                borderRight: '1px solid rgba(46,90,72,0.18)',
                textDecoration:'none', color:'inherit',
              }}>
                <div style={{fontSize:10.5, fontWeight:700, letterSpacing:'0.16em', textTransform:'uppercase', color:C.clay}}>{a.host}</div>
                <div style={{fontSize:13, fontWeight:600, color:C.forest, lineHeight:1.35}}>{a.title}</div>
              </a>
            ))}"""

NEW_RENDER = """hasArticles && (
          <div style={{width:'100%', height:'100%', display:'grid', gridTemplateColumns:`repeat(${slot.articles.length}, 1fr)`, gap:0}}>
            {slot.articles.map(a => (
              <a key={a.url} href={a.url} target="_blank" rel="noopener noreferrer" style={{
                display:'flex', flexDirection:'column',
                background:'#fff',
                borderRight: '1px solid rgba(46,90,72,0.18)',
                textDecoration:'none', color:'inherit',
                overflow:'hidden',
              }}>
                {a.image && (
                  <div style={{height:'48%', minHeight:120, backgroundImage:`url(${a.image})`, backgroundSize:'cover', backgroundPosition:'center'}}/>
                )}
                <div style={{padding:'14px 16px 16px', display:'flex', flexDirection:'column', gap:6, flex:1, background:`linear-gradient(180deg, transparent 0%, ${a.tint||'rgba(46,90,72,0.06)'} 100%)`}}>
                  <div style={{fontSize:10.5, fontWeight:700, letterSpacing:'0.16em', textTransform:'uppercase', color:C.clay}}>{a.host}</div>
                  <div style={{fontSize:14, fontWeight:600, color:C.forest, lineHeight:1.3}}>{a.title}</div>
                  {a.excerpt && (
                    <div style={{fontSize:12.5, color:C.inkSoft, lineHeight:1.5, marginTop:2}}>{a.excerpt}</div>
                  )}
                </div>
              </a>
            ))}"""


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try: return json.loads(raw), m.start(1), m.end(1)
    except: return json.loads(raw.replace('\\"','"').replace('\\u002F','/').replace('\\u003E','>').replace('\\u003C','<')), m.start(1), m.end(1)


def decode(e):
    raw = base64.b64decode(e["data"])
    if e.get("compressed"): raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"): raw = gzip.compress(raw)
    return {"mime": template["mime"], "compressed": template.get("compressed", False), "data": base64.b64encode(raw).decode("ascii")}


def js_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def patch_articles_in_slots(js: str) -> tuple:
    """For each article URL prefix, find {url:'...'} inside articles:[...] and inject image+excerpt."""
    n_changed = 0
    out = js
    for url_key, data in ARTICLES.items():
        # Find a {...url:'...<url_key>...'...} entry
        pat = re.compile(r"\{[^{}]*url:'[^']*" + re.escape(url_key) + r"[^']*'[^{}]*\}")
        m = pat.search(out)
        if not m:
            print(f"  not found: {url_key}")
            continue
        entry = m.group(0)
        if "image:" in entry and "excerpt:" in entry:
            # already patched, replace anyway to keep config in sync (idempotent re-write)
            # Strip old image and excerpt
            for k in ("image", "excerpt"):
                entry = re.sub(r",\s*" + k + r":'(?:\\'|[^'])*'", "", entry)
        # Inject before closing brace
        inject = ", image:" + js_str(data["image"]) + ", excerpt:" + js_str(data["excerpt"])
        new_entry = entry[:-1].rstrip() + inject + " }"
        out = out[:m.start()] + new_entry + out[m.end():]
        n_changed += 1
        print(f"  {url_key} -> image + excerpt added")
    return out, n_changed


def patch_render(js: str) -> int:
    if NEW_RENDER.split("\n")[1].strip() in js and "a.excerpt" in js:
        print("  render already patched")
        return 0
    if OLD_RENDER not in js:
        print("  ERROR: target render block not found verbatim")
        return -1
    return js.replace(OLD_RENDER, NEW_RENDER).count(NEW_RENDER) and js.replace(OLD_RENDER, NEW_RENDER)


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded {BUNDLE_UUID[:8]}: {len(js)} chars")

    js, n = patch_articles_in_slots(js)
    print(f"Articles patched: {n}")

    r = patch_render(js)
    if isinstance(r, str):
        js = r
        print("Render block patched")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
