#!/usr/bin/env python3
"""
Follow-up to patch_structural_v1.py — catches two Donate buttons we missed:

  1. The "Join our movement" CTA banner (CTAbanner, defined in About bundle
     4b635b80, used on multiple pages). Remove the Donate PillButton so only
     "Get involved" remains.

  2. The Footer ENGAGE column (Footer in Nav bundle 7beb661d) has links for
     impact, gallery, news, get-involved, donate, contact. Drop the donate and
     news entries to align with the hidden-from-nav decision.

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
ABOUT_BUNDLE = "4b635b80-8097-4e91-be52-33c15e1430e3"   # CTAbanner
NAV_BUNDLE   = "7beb661d-7acd-4a87-a01d-94a588491f3c"   # Footer


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


def patch_cta_banner(js):
    """Remove the Donate PillButton from the CTAbanner JSX."""
    old = '<PillButton variant="white" onClick={onDonate}>Donate <Icon name="arrow" size={14}/></PillButton>\n        '
    if old in js:
        js = js.replace(old, "")
        return js, "CTAbanner Donate button removed"
    if 'onClick={onDonate}>Donate' not in js:
        return js, "CTAbanner Donate already removed (idempotent)"
    return js, "CTAbanner Donate pattern not matched verbatim"


def patch_footer(js):
    """Drop 'donate' and 'news' entries from the Footer ENGAGE array."""
    old = "[['impact','Impact & Stories'],['gallery','Gallery & Media'],['news','Updates & News'],['get-involved','Get Involved'],['donate','Donate'],['contact','Contact']]"
    new = "[['impact','Impact & Stories'],['gallery','Gallery & Media'],['get-involved','Get Involved'],['contact','Contact']]"
    if old in js:
        js = js.replace(old, new)
        return js, "Footer ENGAGE: dropped 'news' and 'donate'"
    if new in js:
        return js, "Footer ENGAGE already trimmed (idempotent)"
    return js, "Footer ENGAGE array not matched verbatim — inspect Footer manually"


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)

    # CTAbanner
    about = manifest[ABOUT_BUNDLE]
    js = decode(about)
    js, msg = patch_cta_banner(js)
    manifest[ABOUT_BUNDLE] = encode(js, about)
    print(f"About bundle: {msg}")

    # Footer
    nav = manifest[NAV_BUNDLE]
    js = decode(nav)
    js, msg = patch_footer(js)
    manifest[NAV_BUNDLE] = encode(js, nav)
    print(f"Nav bundle:   {msg}")

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
