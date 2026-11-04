"""qa_sheets.py TOUR OUT [--per 25]: page a warp tour into contact sheets for qa_gate.py, every scene's distinct frames,
each tile labelled, big enough to tell English from Japanese. Prints what it dropped as near-duplicates, per scene total.

    python -X utf8 tools/qa_sheets.py work/qa/tour work/qa/tour_sheets
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

TILE_W, TILE_H, LABEL_H, COLS = 256, 192, 11, 5
SAME = 0.02  # share of pixels that must change for a frame to count as new


def distinct(frames):
    """The frames that differ from the last one kept, plus the last frame."""
    kept, last = [], None
    for f in frames:
        im = Image.open(f).convert("RGB").resize((160, 120), Image.BILINEAR)
        a = np.asarray(im, dtype=np.int16)
        if last is None or (np.abs(a - last).max(axis=2) > 24).mean() > SAME:
            kept.append(f)
            last = a
    if frames and frames[-1] not in kept:
        kept.append(frames[-1])
    return kept


def lit(frame):
    """Not a blank frame: a black screen tells a reader nothing."""
    return np.asarray(Image.open(frame).convert("L")).max() > 24


def pages(tour):
    tiles, dropped = [], 0
    for scene in sorted(p for p in Path(tour).iterdir() if p.is_dir() and not p.name.startswith("_")):
        frames = sorted(scene.glob("f*.png"))
        keep = [f for f in distinct(frames) if lit(f)]
        dropped += len(frames) - len(keep)
        tiles += [(scene.name, f) for f in keep]
    return tiles, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tour")
    ap.add_argument("out")
    ap.add_argument("--per", type=int, default=25)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("sheet_*.png"):
        old.unlink()
    tiles, dropped = pages(a.tour)
    index = []
    for n in range(0, len(tiles), a.per):
        page = tiles[n:n + a.per]
        rows = (len(page) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * TILE_W, rows * (TILE_H + LABEL_H)), (60, 0, 60))
        dr = ImageDraw.Draw(sheet)
        name = f"sheet_{n // a.per:03}"
        for i, (scene, f) in enumerate(page):
            x, y = (i % COLS) * TILE_W, (i // COLS) * (TILE_H + LABEL_H)
            sheet.paste(Image.open(f).convert("RGB").resize((TILE_W, TILE_H), Image.LANCZOS), (x, y + LABEL_H))
            dr.text((x + 2, y), f"{scene} {f.stem}", fill=(255, 255, 0))
            index.append(f"{name}\t{scene}\t{f.stem}")
        sheet.save(out / f"{name}.png")
    (out / "index.tsv").write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(tiles)} frames on {(len(tiles) + a.per - 1) // a.per} sheets, {dropped} near-duplicate or blank frames dropped")


if __name__ == "__main__":
    sys.exit(main())
