#!/usr/bin/env python3
"""
Sort Russel's final photos from _incoming/final_photos/ into images/PageN/.

Russel named every file with a slot-ID prefix (e.g. 5.2.png, 4.9.jpg) per the v2
manifest, so routing is purely by the prefix.

Single-photo slots:  X.Y.<ext>  ->  images/Page<page>/X.Y_<descriptor>.<ext>
Gallery folders:     Gallery/8.X/*  ->  images/Page8/8.X_NN.<ext>

Before copying, removes any pre-existing files in the target dir whose name starts
with the same slot prefix, so re-running this script is idempotent and we don't end
up with stale + new versions both globbed by enrich_slots.

Special handling:
  4.9 changes species: Black Rat -> Orange-bellied Himalayan Squirrel
  6.2 and 6.3 transition from MISSING to filled (architect renders)
"""
import os
import re
import shutil
import glob
from pathlib import Path

ROOT = Path("/sessions/intelligent-kind-planck/mnt/pittachhara/website/development")
SRC = ROOT / "_incoming/final_photos"
IMAGES = ROOT / "images"

# Descriptor per slot — used as the suffix in the final filename (the part after X.Y_)
# The enrich_slots glob is X.Y_* so any suffix works; this is purely for human readability.
SLOT_DESC = {
    "1.5":  "library",
    "2.2":  "forest_landscape_v2",
    "3.4":  "mhm_v2",
    "3.5":  "library",
    "3.7":  "nursery",
    "4.2":  "macaque",
    "4.3":  "slow_loris",
    "4.4":  "leopard_cat",
    "4.5":  "indian_civet",
    "4.6":  "mongoose",
    "4.7":  "palm_civet",
    "4.8":  "tree_shrew",
    "4.9":  "squirrel",          # SPECIES CHANGED: was Black Rat
    "4.10": "birds",
    "4.11": "reptiles",
    "4.12": "camera_trap_v2",
    "5.2":  "regeneration",
    "5.3":  "agroforestry",
    "5.4":  "corridor",
    "5.5":  "stream_v2",
    "6.2":  "cottage_render",    # NEW: was MISSING (architect render)
    "6.3":  "research_centre",   # NEW: was MISSING (architect render)
}

# Gallery folders that should expand into numbered files inside images/Page8/
GALLERY_FOLDERS = {"8.1", "8.2", "8.3", "8.5"}

# Loose gallery files (e.g. Gallery/8.4.jpg) treated as single-photo galleries
GALLERY_LOOSE_PATTERN = re.compile(r"^(8\.\d+)\.([a-zA-Z]+)$")


def page_of(sid):
    return int(sid.split(".")[0])


def clean_ext(name):
    ext = name.rsplit(".", 1)[-1].lower()
    return "jpg" if ext == "jpeg" else ext


def clear_slot_in_target(slot_id, page_n):
    """Delete any existing files in images/Page<n>/ that start with slot_id_."""
    target_dir = IMAGES / f"Page{page_n}"
    target_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(target_dir / f"{slot_id}_*")
    removed = 0
    for old in glob.glob(pattern):
        os.remove(old)
        removed += 1
    return removed


def copy_single(src_path, slot_id):
    """Copy a single-photo slot file into images/Page<n>/slot_<descriptor>.<ext>."""
    page_n = page_of(slot_id)
    descriptor = SLOT_DESC.get(slot_id, "photo")
    ext = clean_ext(src_path.name)
    new_name = f"{slot_id}_{descriptor}.{ext}"
    target_dir = IMAGES / f"Page{page_n}"
    target_dir.mkdir(parents=True, exist_ok=True)
    removed = clear_slot_in_target(slot_id, page_n)
    target = target_dir / new_name
    shutil.copy2(src_path, target)
    return target, removed


def copy_gallery(src_folder, slot_id):
    """Copy every file inside Gallery/8.X/ into images/Page8/ with numbered suffixes."""
    page_n = page_of(slot_id)
    target_dir = IMAGES / f"Page{page_n}"
    target_dir.mkdir(parents=True, exist_ok=True)
    removed = clear_slot_in_target(slot_id, page_n)
    files = sorted(f for f in src_folder.iterdir() if f.is_file())
    placed = []
    for i, f in enumerate(files, start=1):
        ext = clean_ext(f.name)
        # Skip non-image files for now (videos handled separately if needed)
        if ext not in {"jpg", "png", "webp", "gif"}:
            continue
        new_name = f"{slot_id}_{i:02d}.{ext}"
        target = target_dir / new_name
        shutil.copy2(f, target)
        placed.append(target.name)
    return placed, removed


def main():
    print(f"Source: {SRC}")
    print(f"Target: {IMAGES}\n")
    summary = {"singles": 0, "removed": 0, "galleries": {}}

    # 1. Top-level single-photo files
    print("=== Single-photo slots ===")
    for f in sorted(SRC.iterdir()):
        if not f.is_file():
            continue
        m = re.match(r"^(\d+\.\d+)\.[a-zA-Z]+$", f.name)
        if not m:
            print(f"  skip (no slot prefix): {f.name}")
            continue
        slot_id = m.group(1)
        target, removed = copy_single(f, slot_id)
        summary["singles"] += 1
        summary["removed"] += removed
        print(f"  {f.name:18}  ->  {target.relative_to(ROOT)}  (cleared {removed} stale)")

    # 2. Gallery folders
    print("\n=== Gallery folders ===")
    gallery_root = SRC / "Gallery"
    if gallery_root.exists():
        for child in sorted(gallery_root.iterdir()):
            if child.is_dir() and child.name in GALLERY_FOLDERS:
                placed, removed = copy_gallery(child, child.name)
                summary["galleries"][child.name] = len(placed)
                print(f"  Gallery/{child.name}/  ->  images/Page8/  ({len(placed)} files, cleared {removed} stale)")
            elif child.is_file():
                m = GALLERY_LOOSE_PATTERN.match(child.name)
                if m:
                    slot_id, _ = m.groups()
                    # Treat as a single-photo gallery (rename to 8.X_01.ext)
                    page_n = page_of(slot_id)
                    target_dir = IMAGES / f"Page{page_n}"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    removed = clear_slot_in_target(slot_id, page_n)
                    ext = clean_ext(child.name)
                    new_name = f"{slot_id}_01.{ext}"
                    target = target_dir / new_name
                    shutil.copy2(child, target)
                    summary["galleries"][slot_id] = 1
                    print(f"  Gallery/{child.name}  ->  images/Page8/{new_name}  (cleared {removed})")

    # 3. News content (just inventory; routing decision is Nabil's)
    print("\n=== News content (parked for Nabil's call) ===")
    news_root = SRC / "News"
    if news_root.exists():
        for child in sorted(news_root.iterdir()):
            if child.is_file():
                print(f"  {child.name}  ({child.stat().st_size/1024/1024:.1f} MB)")

    print(f"\nSummary: {summary['singles']} single-photo slots, "
          f"galleries: {summary['galleries']}, "
          f"{summary['removed']} stale files cleared.")


if __name__ == "__main__":
    main()
