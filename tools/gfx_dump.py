"""gfx_dump.py OUTDIR: render every picture that needs English to PNG, zoomed, with its TIM facts on stdout. Read-only.
docs/re/graphics.md lists the rows."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import timscan
from PIL import Image

KUDO = ROOT / "work/tree/ESCA/TIM/KUDO"
RAW = ["ESCA111", "ZZZZZ2", "ZZZZZ3", "ST_TITL"] + [f"TI0{i}" for i in range(1, 8)]
STAFF = ROOT / "work/tree/ESCA/PRG/STAFF.BIN"


def save(d, t, path):
    im = timscan.render(d, t).convert("RGBA")
    bg = Image.new("RGBA", im.size, (60, 0, 60, 255))
    bg.alpha_composite(im)
    bg.save(path)
    pal = t["clut"]
    print(path.name, f"bpp{t['bpp']} {t['w']}x{t['h']} vram {t['x']},{t['y']} clut {t['cx']},{t['cy']} {t.get('cw')}x{t.get('ch')} off {t['off']:#x}")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for n in RAW:
        d = (KUDO / f"{n}.TIM").read_bytes()
        for i, t in enumerate(timscan.scan(d)):
            save(d, t, out / f"{n}_{i}.png")
    d = STAFF.read_bytes()
    for off, dec, t in timscan.scan_lz(d):
        save(dec, t, out / f"STAFF_{off:X}.png")
