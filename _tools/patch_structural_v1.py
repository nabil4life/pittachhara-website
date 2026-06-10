#!/usr/bin/env python3
"""
Structural changes from the team meeting + Russel correspondence (June 2026):

  1. Hide News entry from main navigation (route stays alive, just not in the menu).
  2. Hide the Donate PillButton from header + mobile menu, and hide the floating
     PittaCTA "heart" donate button. Donate route stays alive at /#/donate so we
     can re-enable later.
  3. Remove Md. Jahidul Kabir from the TRUSTEES array (Page 2). The grid layout
     auto-rebalances to 12 cards.
  4. Wire the contact form (Page 12) to Formspree. Uses a placeholder FORM_ID;
     Nabil supplies the real one after signing up at formspree.io (free).

Idempotent.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
NAV_BUNDLE = "7beb661d-7acd-4a87-a01d-94a588491f3c"
ABOUT_BUNDLE = "4b635b80-8097-4e91-be52-33c15e1430e3"
CONTACT_BUNDLE = "23c669aa-6716-4ddd-ab28-32729c9c7a83"

# Formspree placeholder — replace with real ID once Nabil signs up
FORMSPREE_ID = "REPLACE_WITH_FORMSPREE_ID"


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


# -- patches -----------------------------------------------------------------

def patch_nav(js):
    changed = []

    # 1a. Remove the News entry from nav items
    old_news = "  { k:'news',         label:'News' },\n"
    if old_news in js:
        js = js.replace(old_news, "")
        changed.append("removed News from nav items")
    elif "{ k:'news'" not in js:
        changed.append("News already removed (idempotent)")

    # 1b. Hide desktop Donate PillButton (the one inside the desktop header)
    # Find the line and wrap with {false && (...)} or comment it out
    old_donate_desktop = '<PillButton variant="clay" onClick={onDonate} style={{padding:\'9px 20px\', fontSize:13.5}}>Donate</PillButton>'
    new_donate_desktop = "{/* Donate hidden for launch */}"
    if old_donate_desktop in js:
        js = js.replace(old_donate_desktop, new_donate_desktop)
        changed.append("hid desktop Donate button")
    elif new_donate_desktop in js:
        changed.append("desktop Donate already hidden")

    # 1c. Hide mobile Donate PillButton
    old_donate_mobile = '<PillButton variant="clay" onClick={()=>{onDonate(); setMobile(false);}} style={{width:\'100%\', justifyContent:\'center\'}}>Donate</PillButton>'
    new_donate_mobile = "{/* Donate hidden for launch */}"
    if old_donate_mobile in js:
        js = js.replace(old_donate_mobile, new_donate_mobile)
        changed.append("hid mobile Donate button")

    # 1d. Hide PittaCTA floating button (return null early)
    old_pitta = "const PittaCTA = ({ onClick }) => {\n  const [pressed, setPressed] = useSN(false);\n  return ("
    new_pitta = "const PittaCTA = ({ onClick }) => {\n  return null; // Donate CTA hidden for launch\n  // eslint-disable-next-line no-unreachable\n  const [pressed, setPressed] = useSN(false);\n  return ("
    if old_pitta in js and "return null; // Donate CTA hidden" not in js:
        js = js.replace(old_pitta, new_pitta)
        changed.append("hid PittaCTA floating button")
    elif "return null; // Donate CTA hidden" in js:
        changed.append("PittaCTA already hidden")

    return js, changed


def patch_about(js):
    """Remove Md. Jahidul Kabir entry from TRUSTEES array."""
    # The entry: { name:'Md. Jahidul Kabir', role:'Technical Advisor · Bangladesh Forest Department', bio:'...' },
    pat = re.compile(r"\s*\{[^{}]*name:'Md\. Jahidul Kabir'[^{}]*\},?", re.DOTALL)
    m = pat.search(js)
    if m:
        # Strip the entry and any trailing comma+whitespace before the closing ]
        js = pat.sub("", js, count=1)
        # If we removed the last entry leaving "{...},]", trim the stray comma
        js = re.sub(r",(\s*\])", r"\1", js)
        return js, "removed Kabir trustee entry"
    return js, "Kabir entry already removed (idempotent)"


def patch_contact(js, form_id):
    """Replace the contact form's fake onSubmit with a Formspree fetch."""
    old = "<form onSubmit={e=>{e.preventDefault(); setSent(true);}}>"
    new = (
        "<form onSubmit={async e=>{\n"
        "                e.preventDefault();\n"
        f"                const FORM_ID = '{form_id}';\n"
        "                try {\n"
        "                  const r = await fetch('https://formspree.io/f/' + FORM_ID, {\n"
        "                    method:'POST',\n"
        "                    headers:{'Accept':'application/json','Content-Type':'application/json'},\n"
        "                    body: JSON.stringify(form),\n"
        "                  });\n"
        "                  if (r.ok) setSent(true);\n"
        "                  else alert('Sorry, that did not send. Please email contact@pittachhara.org directly.');\n"
        "                } catch (err) {\n"
        "                  alert('Sorry, that did not send. Please email contact@pittachhara.org directly.');\n"
        "                }\n"
        "              }}>"
    )
    if old in js:
        js = js.replace(old, new)
        return js, "wired contact form to Formspree (placeholder ID)"
    elif "https://formspree.io/f/" in js:
        return js, "contact form already wired to Formspree (idempotent)"
    return js, "ERROR: contact form onSubmit not found"


# -- runner ------------------------------------------------------------------

def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)

    # Nav bundle
    nav = manifest[NAV_BUNDLE]
    js = decode(nav)
    js, nav_changes = patch_nav(js)
    manifest[NAV_BUNDLE] = encode(js, nav)
    print("Nav bundle:")
    for c in nav_changes: print(f"  - {c}")

    # About bundle (TRUSTEES)
    about = manifest[ABOUT_BUNDLE]
    js = decode(about)
    js, msg = patch_about(js)
    manifest[ABOUT_BUNDLE] = encode(js, about)
    print(f"About bundle:\n  - {msg}")

    # Contact bundle (form)
    contact = manifest[CONTACT_BUNDLE]
    js = decode(contact)
    js, msg = patch_contact(js, FORMSPREE_ID)
    manifest[CONTACT_BUNDLE] = encode(js, contact)
    print(f"Contact bundle:\n  - {msg}")

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:ms] + "\n" + new_json + html[me:])
    print("Done")


if __name__ == "__main__":
    main()
