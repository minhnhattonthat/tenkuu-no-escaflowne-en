"""gfx_sweep.py OUTDIR [--count]: static graphics sweep. Every raw and LZ TIM in every game file, deduped by pixels,
rendered to numbered sheets + index.tsv. Files with no TIM, and files whose bytes aren't accounted for, are printed."""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import timscan
from PIL import Image, ImageDraw

TREE = ROOT / "work/tree"
SKIP_SUF = {".STR", ".WAV", ".DAT", ".CNF"}
SKIP_DIR = {"SOUND"}


def files():
    for f in sorted(TREE.rglob("*")):
        if not f.is_file():
            continue
        if f.parts[-2] in SKIP_DIR or f.suffix.upper() in SKIP_SUF or f.name == "license_data.dat":
            print("skip (not scanned):", f.relative_to(TREE))
            continue
        yield f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--per", type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    idx = (out / "index.tsv").open("w", encoding="utf-8", newline="\n")
    idx.write("id\tfile\toffset\tkind\tbpp\tw\th\tvram\tclut\tdup_of\tsheet\n")
    seen, items, sheet_no, n = {}, [], 0, 0

    def flush():
        global sheet_no, items
        if not items:
            return
        tile, cols = 240, 6
        rows = (len(items) + cols - 1) // cols
        S = Image.new("RGB", (cols * tile, rows * (tile + 12)), (60, 0, 60))
        dr = ImageDraw.Draw(S)
        for i, (tid, im) in enumerate(items):
            x, y = (i % cols) * tile, (i // cols) * (tile + 12)
            k = min(1, (tile - 2) / im.width, (tile - 2) / im.height)
            if k < 1:
                im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))))
            S.paste(im, (x, y + 12), im)
            dr.text((x + 1, y), tid, fill=(255, 255, 0))
        S.save(out / f"sheet_{sheet_no:03d}.png")
        sheet_no += 1
        items = []

    for f in files():
        d = f.read_bytes()
        raw = [(t["off"], d, t, "raw") for t in timscan.scan(d)]
        lzs = [(o, b, t, "lz") for o, b, t in timscan.scan_lz(d)]
        rel = f.relative_to(TREE).as_posix()
        print(f"{rel}: {len(raw)} raw, {len(lzs)} lz, {len(d)} bytes")
        for off, b, t, kind in raw + lzs:
            h = hashlib.sha1(b[t["pix"]:t["end"]]).hexdigest()
            dup = seen.get(h, "")
            tid = "G%05d" % n
            n += 1
            idx.write(f"{tid}\t{rel}\t{off:X}\t{kind}\t{t['bpp']}\t{t['w']}\t{t['h']}\t{t['x']},{t['y']}\t{t['cx']},{t['cy']}\t{dup}\tsheet_{sheet_no:03d}\n")
            if dup or a.count:
                seen.setdefault(h, tid)
                continue
            seen[h] = tid
            try:
                items.append((f"{tid} {f.name[:9]} {off:X}", timscan.render(b, t).convert("RGBA")))
            except ValueError as e:
                print("  cannot render", rel, hex(off), e)
            if len(items) >= a.per:
                flush()
    flush()
    idx.close()
    print(n, "TIMs,", len(seen), "unique,", sheet_no, "sheets")
