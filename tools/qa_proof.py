"""qa_proof.py TOUR OUT: the graphics text rows, zoomed: from each named scene's frames, the brightest, 2x, labelled.
Phase 8's rule for graphics text: English in a zoomed cold-boot shot. Run the card scenes with a short --shot-every first,
or a card's fade can fall between shots.

    python -X utf8 tools/debug/warp_all.py --cue build/escaflowne_en.cue --out work/qa/proof --shot-every 30 ch1_card ...
    python -X utf8 tools/qa_proof.py work/qa/proof work/qa/proof_sheets
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

COLS, ROWS, ZOOM = 3, 3, 2
LAST_SHOTS = 15
TILE_W, TILE_H, LABEL_H = 320 * ZOOM, 240 * ZOOM, 12


def brightest(scene):
    """A card at the top of its fade. Only the run's last shots: before them is the boot's own video, far brighter."""
    return max(sorted(scene.glob("f*.png"))[-LAST_SHOTS:], key=lambda f: np.asarray(Image.open(f).convert("L"), dtype=np.float32).mean())


def main(tour, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scenes = sorted(p for p in Path(tour).iterdir() if p.is_dir() and not p.name.startswith("_"))
    tiles = [(s.name, brightest(s)) for s in scenes if any(s.glob("f*.png"))]
    for n in range(0, len(tiles), COLS * ROWS):
        sheet = Image.new("RGB", (COLS * TILE_W, ROWS * (TILE_H + LABEL_H)), (60, 0, 60))
        draw = ImageDraw.Draw(sheet)
        for i, (name, frame) in enumerate(tiles[n:n + COLS * ROWS]):
            x, y = i % COLS * TILE_W, i // COLS * (TILE_H + LABEL_H)
            draw.text((x + 2, y), f"{name} {frame.stem}", fill=(255, 255, 0))
            sheet.paste(Image.open(frame).convert("RGB").resize((TILE_W, TILE_H), Image.NEAREST), (x, y + LABEL_H))
        sheet.save(out / f"sheet_proof_{n // (COLS * ROWS):03d}.png")  # qa_gate.py takes sheet_*
    print(f"{len(tiles)} scenes on {(len(tiles) + COLS * ROWS - 1) // (COLS * ROWS)} sheets")


if __name__ == "__main__":
    main(*sys.argv[1:3])
