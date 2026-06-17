#!/usr/bin/env python3
"""
Round 3 (June 2026):
  1. Research card (bundle 3a22a8a7): correct the paper title, author list and summary
     to the real paper (Shawon et al. 2024; DOI 10.3390/ani14243568 was already right).
  2. Research hero banner: the survey was not continuous (Feb-May 2023, Oct 2023-Aug 2024),
     so "18 months of continuous monitoring" -> "18 months of camera-trap monitoring".
  3. Eco-Resort (bundle 23c669aa): add image 4.12 to "Wildlife research participation".
  4. Remove the Press kit section (bundle 23c669aa).

About page already reads the requested wording, so it is left unchanged.
String replacements assert their counts so a rerun fails loudly rather than corrupting.
"""
import re, json, gzip, base64
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
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


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ABORT [{label}]: expected 1 occurrence, found {n}")
    print(f"  ok: {label}")
    return text.replace(old, new, 1)


# --- new research card content ---
OLD_TITLE = "Mammalian biodiversity in the lowland forests of the Chattogram Hill Tracts, Bangladesh: a camera-trap survey."
NEW_TITLE = "An Assessment of the Diversity and Seasonal Dynamics of Small- and Medium-Sized Mammals in Pittachhara Forest, Bangladesh, Using a Camera Trap Survey."

OLD_AUTHORS = "Kabir, M. J., Ahsan, R., Matsushita, N., Miyaki, T., Hasan, M. K., Habib, A., Tsubota, H., & Aswani, S. (2024)."
NEW_AUTHORS = "Shawon, R. A. R., Rahman, M. M., Iqbal, M. M., Russel, M. A., & Moribe, J. (2024)."

OLD_SUMMARY = "The first comprehensive mammalian survey of the Pittachhara forest. The study documents species distribution across a continuous 18-month camera-trap programme, confirms the presence of globally threatened species, and establishes baseline data for monitoring conservation success. Published open-access."
NEW_SUMMARY = "A camera-trap survey of Pittachhara Forest assessing the diversity and seasonal dynamics of its small- and medium-sized mammals. Across 27 camera-trap stations the study recorded eight mammal species, including the Bengal slow loris, northern pig-tailed macaque and leopard cat, and found significantly higher activity in summer than winter. It establishes baseline data for ongoing monitoring and conservation. Published open-access."

OLD_BANNER = "published findings, and 18 months of continuous monitoring guide every decision we make."
NEW_BANNER = "published findings, and 18 months of camera-trap monitoring guide every decision we make."

OLD_ECO = "Join camera-trap surveys, species counts, and data collection under scientific guidance.', null]"
NEW_ECO = "Join camera-trap surveys, species counts, and data collection under scientific guidance.', '4.12']"

PRESSKIT_RE = re.compile(
    r"\s*<section style=\{\{background:C\.cream200, padding:'56px 28px 96px'\}\}>.*?</section>",
    re.DOTALL)


def main():
    html = HTML_PATH.read_text()
    m = re.search(r'(<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>)(.+?)(</script>)', html, re.DOTALL)
    raw = m.group(2)
    cand = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<')
    manifest = json.loads(cand)

    print("[WORK 3a22a8a7] research card + banner")
    W = decode(manifest[WORK])
    W = replace_once(W, OLD_TITLE, NEW_TITLE, "paper title")
    W = replace_once(W, OLD_AUTHORS, NEW_AUTHORS, "paper authors")
    W = replace_once(W, OLD_SUMMARY, NEW_SUMMARY, "paper summary")
    W = replace_once(W, OLD_BANNER, NEW_BANNER, "banner: continuous -> camera-trap")
    manifest[WORK] = encode(W, manifest[WORK])

    print("[GALLERY 23c669aa] eco-resort 4.12 + press kit removal")
    G = decode(manifest[GALLERY])
    G = replace_once(G, OLD_ECO, NEW_ECO, "eco-resort: add 4.12")
    G, n = PRESSKIT_RE.subn("", G)
    if n != 1:
        raise SystemExit(f"ABORT: press-kit section matched {n} times")
    print("  ok: press kit section removed")
    if "Press kit" in G or "press kit" in G:
        raise SystemExit("ABORT: 'press kit' still present after removal")
    manifest[GALLERY] = encode(G, manifest[GALLERY])

    new_json = json.dumps(manifest, separators=(",", ":"))
    HTML_PATH.write_text(html[:m.start(2)] + "\n" + new_json + html[m.end(2):])
    print("\nDone — 2 bundles patched, index.html written.")


if __name__ == "__main__":
    main()
