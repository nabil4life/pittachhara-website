#!/usr/bin/env python3
"""
Enrich SLOTS object inside the Pittachhara standalone HTML bundle.

The standalone HTML embeds React component scripts as gzipped+base64 entries
in a JSON manifest. The Home page component file (UUID f78573f1...) holds the
SLOTS object that maps slot IDs (e.g. "2.3") to render metadata. To make
Pages 2-12 render real images, we set the `real:`, `realLogos:`, or
`youtubeUrl:` fields on each slot. The component then renders <img src=slot.real>
which the browser loads directly.

Usage: edit PAGE_CONFIG below for the page you want to wire, then run.
The script is idempotent: re-running with the same config produces the same file.
"""
import re
import os
import sys
import json
import gzip
import base64
import shutil
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BACKUP_PATH = Path(__file__).parent.parent / "index.original.html"
SLOTS_BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

# ---- per-page slot configuration --------------------------------------------
# kind 'image' → set real:'<path>'
# kind 'gallery' → set realLogos:[{src,alt}, ...]
# kind 'video' → set youtubeUrl:'<url>'

PAGE1_OVERRIDES = {
    "1.1":  {"real": "images/Page1/1.1_hero_drone_video.mp4"},   # video replaces static
    "1.5":  {"real": "images/Page1/1.5_library.png"},            # NEW: real library photo (was medical-centre stand-in)
    "1.10": {"real": "images/Page1/1.10_founder_russel_v2.jpg"}, # new portrait
}

PAGE2_CONFIG = {
    "2.1": {"real": "images/Page2/2.1_hero_about.mp4"},  # video hero
    "2.2": {"real": "images/Page2/2.2_forest_landscape_v2.jpg"},  # Russel replacement June 2026
    "2.3": {"realLogos": "auto:images/Page2/2.3_trustee_*"},   # 13 trustees
    "2.4": {"real": "images/Page2/2.4_map.jpg"},
    # 2.5 MDPI paper — MISSING
    "2.6": {"youtubeUrl": "https://www.youtube.com/watch?v=IGxbIgCPCSA"},
    "2.7": {"real": "images/Page2/2.7_balipara_award.jpg"},
    "2.8": {"realLogos": "auto:images/Page2/2.8_logo_*"},      # 4 partner logos
    "2.9": {"realLogos": "auto:images/Page2/2.9_programme_*"}, # 6 activity photos
}

PAGE3_CONFIG = {
    "3.1": {"real": "images/Page3/3.1_forest_conservation.jpg"},  # card image; hero video lives in SLOTS['3.1hero'] via patch_page3_hero.py
    # 3.5 Community Library — MISSING (Russel to supply); handled by patch_page3_hero.py
    # 3.7 Native Plant Nursery — MISSING (Russel to supply)
    "3.2": {"real": "images/Page3/3.2_wildlife_research.jpg"},
    "3.3": {"real": "images/Page3/3.3_free_health.jpg"},
    "3.4": {"real": "images/Page3/3.4_mhm_v2.jpg"},  # Russel replacement June 2026
    "3.5": {"real": "images/Page3/3.5_library.png"},  # NEW: Russel supplied (June 2026)
    "3.6": {"real": "images/Page3/3.6_wildlife_rescue.jpg"},
    # 3.7 Native Plant Nursery — MISSING
    "3.8": {"real": "images/Page3/3.8_womens_empowerment.jpg"},
    "3.9": {"real": "images/Page3/3.9_conservation_education.jpg"},
}

PAGE4_CONFIG = {
    "4.1": {"real": "images/Page4/4.1_research_hero.jpg"},
    "4.2": {"real": "images/Page4/4.2_macaque.jpg"},
    "4.3": {"real": "images/Page4/4.3_slow_loris.jpg"},
    "4.4": {"real": "images/Page4/4.4_leopard_cat.jpg"},
    "4.5": {"real": "images/Page4/4.5_indian_civet.jpg"},
    "4.6": {"real": "images/Page4/4.6_mongoose.jpg"},
    "4.7": {"real": "images/Page4/4.7_palm_civet.jpg"},
    "4.8": {"real": "images/Page4/4.8_tree_shrew.jpg"},
    "4.9": {"real": "images/Page4/4.9_black_rat.jpg"},
    # 4.10 Birds — MISSING
    # 4.11 Reptiles & Amphibians — MISSING
    "4.12": {"real": "images/Page4/4.12_camera_trap_v2.jpg"},  # Russel replacement June 2026
    # 4.13 MDPI paper — MISSING
    "4.14": {"realLogos": "auto:images/Page4/4.14_logo_*"},
}

PAGE5_CONFIG = {
    "5.1": {"real": "images/Page5/5.1_hero_drone.jpg"},
    # 5.2 Assisted Natural Regeneration — MISSING
    # 5.3 Smallholder agroforestry — MISSING
    # 5.4 Wildlife corridor — MISSING
    "5.5": {"real": "images/Page5/5.5_stream_v2.jpg"},  # Russel replacement June 2026
    "5.6": {"real": "images/Page5/5.6_tribal_community.jpg"},
    "5.7": {"real": "images/Page5/5.7_forest_dept.jpg"},
}

PAGE6_CONFIG = {
    # 6.1, 6.5 — still awaiting architect renders
    "6.2": {"real": "images/Page6/6.2_cottage_render.jpg"},     # NEW: architect render from Russel
    "6.3": {"real": "images/Page6/6.3_research_centre.jpg"},    # NEW: architect render from Russel
    "6.4": {"real": "images/Page6/6.4_forest_walks_standin.jpg"},
    "6.6": {"real": "images/Page6/6.6_cultural.jpg"},
}

PAGE7_CONFIG = {
    "7.1": {"real": "images/Page7/7.1_health_story.jpg"},
    # 7.2 Women's Empowerment Story — MISSING
    # 7.3 Education & Opportunity Story — MISSING
    # 7.4 Wildlife Rescue & Release Story — MISSING
    "7.5": {"real": "images/Page7/7.5_before_2016.jpg"},
    "7.6": {"real": "images/Page7/7.6_after_2026.jpg"},
    # 7.7 Founder 2016 archive — MISSING
}

PAGE8_CONFIG = {
    "8.1": {"realLogos": "auto:images/Page8/8.1_gallery_*"},   # 4 wildlife / camera traps
    "8.2": {"realLogos": "auto:images/Page8/8.2_forest_*"},    # 4 forest
    "8.3": {"realLogos": "auto:images/Page8/8.3_community_*"}, # 4 community programmes
    # 8.4 Nursery & Restoration gallery — MISSING
    "8.5": {"realLogos": "auto:images/Page8/8.5_rescue_*"},    # 4 wildlife rescue
    "8.6": {"youtubeUrl": "https://www.youtube.com/watch?v=IGxbIgCPCSA"},
    "8.7": {"real": "images/Page8/8.7_aerial.jpg"},
}

PAGE9_CONFIG = {
    "9.1": {"real": "images/Page9/9.1_launch_drone.jpg"},
    "9.2": {"real": "images/Page9/9.2_mdpi_species.jpg"},
    "9.3": {"real": "images/Page9/9.3_iucn_logo.png"},
    "9.4": {"real": "images/Page9/9.4_bbc_still.jpg"},
}

PAGE10_CONFIG = {
    "10.1": {"real": "images/Page10/10.1_get_involved_hero.jpg"},
    "10.2": {"real": "images/Page10/10.2_donate_tile.jpg"},
    "10.3": {"real": "images/Page10/10.3_volunteer_tile.jpg"},
    "10.4": {"real": "images/Page10/10.4_research_tile.jpg"},
    "10.5": {"real": "images/Page10/10.5_corporate_tile.jpg"},
}

PAGE11_CONFIG = {
    "11.1": {"real": "images/Page11/11.1_donate_hero.jpg"},
    "11.2": {"realLogos": "auto:images/Page11/11.2_tier_*"},   # 6 giving level tiles
}

PAGE12_CONFIG = {
    "12.1": {"real": "images/Page12/12.1_contact_hero.jpg"},
}

# Choose which page(s) to apply on this run
ACTIVE_CONFIG = {
    **PAGE1_OVERRIDES,
    **PAGE2_CONFIG, **PAGE3_CONFIG, **PAGE4_CONFIG, **PAGE5_CONFIG,
    **PAGE6_CONFIG, **PAGE7_CONFIG, **PAGE8_CONFIG, **PAGE9_CONFIG,
    **PAGE10_CONFIG, **PAGE11_CONFIG, **PAGE12_CONFIG,
}

# ---- helpers ----------------------------------------------------------------

def expand_glob(pattern: str, alt_prefix: str = "") -> list:
    """auto:images/Page2/2.3_trustee_* -> list of {src, alt} dicts"""
    assert pattern.startswith("auto:"), pattern
    glob_pat = pattern[5:]
    import glob
    files = sorted(glob.glob(str(Path(__file__).parent.parent / glob_pat)))
    result = []
    for f in files:
        rel = os.path.relpath(f, Path(__file__).parent.parent)
        # Use the slot-stripped descriptor as alt text
        base = os.path.basename(f).rsplit(".", 1)[0]
        # Drop the leading "X.Y_" then prettify
        m = re.match(r"\d+\.\d+_(.+)", base)
        alt = (m.group(1) if m else base).replace("_", " ").title()
        result.append({"src": rel, "alt": alt})
    return result


def js_str(s: str) -> str:
    """Quote a python string as a single-quoted JS string literal."""
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def js_obj_arr(arr: list) -> str:
    """[{src,alt}, ...] -> JS array literal."""
    items = []
    for d in arr:
        items.append("{src:" + js_str(d["src"]) + ", alt:" + js_str(d["alt"]) + "}")
    return "[" + ", ".join(items) + "]"


def load_manifest_from_html(html: str) -> tuple:
    """Returns (manifest_dict, start_idx, end_idx) of the manifest <script>."""
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    if not m:
        raise RuntimeError("manifest script tag not found")
    raw = m.group(2)
    candidate = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    return json.loads(candidate), m.start(2), m.end(2)


def write_manifest_into_html(html: str, manifest: dict, start: int, end: int) -> str:
    """Re-serialize manifest as plain JSON. Content inside <script> tags isn't HTML-escaped.

    The only character we'd need to guard against is the literal "</script>" sequence, which
    cannot appear in well-formed JSON of base64+text values (no '<' present).
    Preserve the leading newline the original uses inside the script."""
    new_json = json.dumps(manifest, separators=(",", ":"))
    # The original begins with "\n{..." inside the script tag — keep that shape
    return html[:start] + "\n" + new_json + html[end:]


def decode_script(entry: dict) -> str:
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode_script(text: str, entry_template: dict) -> dict:
    """Returns a fresh entry dict with re-encoded data, preserving mime and compression."""
    raw_bytes = text.encode("utf-8")
    if entry_template.get("compressed"):
        raw_bytes = gzip.compress(raw_bytes)
    return {
        "mime": entry_template["mime"],
        "compressed": entry_template.get("compressed", False),
        "data": base64.b64encode(raw_bytes).decode("ascii"),
    }


def find_balanced_brace_entry(text: str, slot_id: str):
    """Find a SLOTS entry by id, returning (open_brace_idx, close_brace_idx) of its {} block.

    Handles nested braces (e.g. realLogos:[{...}, {...}]) using depth tracking."""
    pat = re.compile(r"'" + re.escape(slot_id) + r"'\s*:\s*\{")
    m = pat.search(text)
    if not m:
        return None
    open_idx = m.end() - 1  # index of '{'
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
                in_str = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return open_idx, i
        i += 1
    return None


def strip_injected_keys(body: str, keys=("real", "realLogos", "youtubeUrl")) -> str:
    """Remove our previously injected key:value pairs from the entry body, regardless of value type."""
    out = body
    for key in keys:
        # Match ",\s*key\s*:\s*<value>" where <value> is a quoted string OR a balanced [...] array.
        # Use depth-aware scanning since regex can't balance brackets safely.
        while True:
            m = re.search(r",\s*" + key + r"\s*:\s*", out)
            if not m:
                break
            v_start = m.end()
            if v_start >= len(out):
                break
            first_ch = out[v_start]
            v_end = None
            if first_ch in ("'", '"'):
                # find matching unescaped quote
                j = v_start + 1
                while j < len(out):
                    if out[j] == '\\':
                        j += 2
                        continue
                    if out[j] == first_ch:
                        v_end = j + 1
                        break
                    j += 1
            elif first_ch == '[':
                depth = 0
                j = v_start
                in_str = False
                q = ''
                while j < len(out):
                    c = out[j]
                    if in_str:
                        if c == '\\':
                            j += 2
                            continue
                        if c == q:
                            in_str = False
                    else:
                        if c in ("'", '"'):
                            in_str = True
                            q = c
                        elif c == '[':
                            depth += 1
                        elif c == ']':
                            depth -= 1
                            if depth == 0:
                                v_end = j + 1
                                break
                    j += 1
            if v_end is None:
                break
            out = out[:m.start()] + out[v_end:]
    return out


def enrich_slot_entry(entry_body: str, config: dict) -> str:
    """Given the contents inside `{ ... }` for one slot, strip prior injections and append new ones."""
    body = strip_injected_keys(entry_body)
    parts = []
    if "real" in config:
        parts.append("real:" + js_str(config["real"]))
    if "realLogos" in config:
        v = config["realLogos"]
        arr = expand_glob(v) if isinstance(v, str) and v.startswith("auto:") else v
        parts.append("realLogos:" + js_obj_arr(arr))
    if "youtubeUrl" in config:
        parts.append("youtubeUrl:" + js_str(config["youtubeUrl"]))
    inject = ", " + ", ".join(parts)
    return body.rstrip() + inject


def main():
    if not HTML_PATH.exists():
        sys.exit(f"HTML not found: {HTML_PATH}")
    if not BACKUP_PATH.exists():
        shutil.copy2(HTML_PATH, BACKUP_PATH)
        print(f"Created backup: {BACKUP_PATH}")
    else:
        print(f"Backup exists: {BACKUP_PATH}")

    html = HTML_PATH.read_text()
    manifest, m_start, m_end = load_manifest_from_html(html)
    print(f"Manifest loaded: {len(manifest)} entries")

    entry = manifest[SLOTS_BUNDLE_UUID]
    js_source = decode_script(entry)
    print(f"Decoded {SLOTS_BUNDLE_UUID[:8]}: {len(js_source)} chars")

    # Find each slot entry (brace-balanced) and rewrite
    changes = []
    for slot_id, slot_cfg in ACTIVE_CONFIG.items():
        loc = find_balanced_brace_entry(js_source, slot_id)
        if loc is None:
            changes.append((slot_id, "NOT FOUND"))
            continue
        open_idx, close_idx = loc
        body = js_source[open_idx + 1:close_idx]
        new_body = enrich_slot_entry(body, slot_cfg)
        js_source = js_source[:open_idx + 1] + new_body + js_source[close_idx:]
        changes.append((slot_id, "updated"))

    # Re-encode
    new_entry = encode_script(js_source, entry)
    manifest[SLOTS_BUNDLE_UUID] = new_entry
    new_html = write_manifest_into_html(html, manifest, m_start, m_end)

    # Sanity: file size shouldn't shrink dramatically
    delta = len(new_html) - len(html)
    print(f"HTML size delta: {delta:+,} chars")

    HTML_PATH.write_text(new_html)
    print(f"Wrote: {HTML_PATH}")
    print("\n--- per-slot changes ---")
    for sid, status in changes:
        print(f"  {sid}: {status}")


if __name__ == "__main__":
    main()
