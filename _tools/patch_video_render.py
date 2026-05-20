#!/usr/bin/env python3
"""
Patch ImageSlot in the f78573f1 React bundle so it renders a <video> element
(autoplay, muted, loop, playsInline) when slot.real ends with .mp4 or .webm.
Otherwise it still renders <img>.

Idempotent: re-running detects the prior patch and skips.
"""
import re, json, base64, gzip
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / "index.html"
BUNDLE_UUID = "f78573f1-64cd-4f59-8544-b39204a866c1"

ORIGINAL = """hasReal && (
          <img
            src={slot.real}
            alt={slot.description}
            style={{width:'100%', height:'100%', objectFit:'cover', display:'block'}}
            loading="lazy"
          />
        )"""

# Conditional render: video for .mp4/.webm, img otherwise
REPLACEMENT = """hasReal && (
          /\\.(mp4|webm)$/i.test(slot.real)
            ? <video
                src={slot.real}
                autoPlay muted loop playsInline
                aria-label={slot.description}
                style={{width:'100%', height:'100%', objectFit:'cover', display:'block'}}
              />
            : <img
                src={slot.real}
                alt={slot.description}
                style={{width:'100%', height:'100%', objectFit:'cover', display:'block'}}
                loading="lazy"
              />
        )"""


def load_manifest(html):
    m = re.search(r'<script[^>]*type=\\?"__bundler/manifest\\?"[^>]*>(.+?)</script>', html, re.DOTALL)
    raw = m.group(1)
    try:
        manifest = json.loads(raw)
    except Exception:
        manifest = json.loads(raw.replace('\\"', '"').replace('\\u002F', '/').replace('\\u003E', '>').replace('\\u003C', '<'))
    return manifest, m.start(1), m.end(1)


def decode(entry):
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def encode(text, template):
    raw = text.encode("utf-8")
    if template.get("compressed"):
        raw = gzip.compress(raw)
    return {
        "mime": template["mime"],
        "compressed": template.get("compressed", False),
        "data": base64.b64encode(raw).decode("ascii"),
    }


def main():
    html = HTML_PATH.read_text()
    manifest, ms, me = load_manifest(html)
    entry = manifest[BUNDLE_UUID]
    js = decode(entry)
    print(f"Decoded f78573f1: {len(js)} chars")

    if "/\\.(mp4|webm)$/i.test(slot.real)" in js:
        print("Already patched — skipping")
        return
    if ORIGINAL not in js:
        print("ERROR: target hasReal block not found verbatim. Aborting to avoid corruption.")
        return

    js = js.replace(ORIGINAL, REPLACEMENT)
    print("hasReal render block patched")

    manifest[BUNDLE_UUID] = encode(js, entry)
    new_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:ms] + "\n" + new_json + html[me:]
    HTML_PATH.write_text(new_html)
    print(f"HTML delta: {len(new_html) - len(html):+,} chars")


if __name__ == "__main__":
    main()
