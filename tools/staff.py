"""staff.py: the staff roll in PRG/STAFF.BIN (overlay loaded at 0x801D8000). Format: docs/re/graphics.md.

    python -X utf8 tools/staff.py OUTDIR    every original line as a labelled strip, for reading (one sheet per TIM)

build() redraws it in English from data/credits.tsv: one sprite per line, packed on the same 4 sheets, the roll's own
order and spacing kept.
"""
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402
import lz  # noqa: E402
import timscan  # noqa: E402

BASE = 0x801D8000
LAYOUT = 0x801D8CBC - BASE  # (line, x, dy) hwords, ending in -1
TABLES = [t - BASE for t in (0x801D90B4, 0x801D93DC, 0x801D9730, 0x801D9A18)]  # the 4 sheets' line tables, in code
STREAMS = [0x1D88, 0x548C, 0x9400, 0xDA44]  # the LZ TIM per sheet, header included (what the code passes to 0x800157CC)
ROW_H = 16
SCREEN_X_MAX = 312
LEFT_X, RIGHT_X = 16, 192
HEADINGS = {3, 42, 81, 97}  # centred on the screen
INK, SHADOW = 15, 1  # the sheets' CLUT is a grey ramp: 0 transparent, 15 near white
GAP = 2  # between lines on a sheet
PAD = 3  # blank columns kept at a sprite's right: the roll's polygon drops the last ones (seen: "Chid" drew as "Chic")


def hw(d, o):
    return struct.unpack_from("<h", d, o)[0]


def read_layout(d):
    o, recs = LAYOUT, []
    while hw(d, o) != -1:
        recs.append((hw(d, o), hw(d, o + 2), hw(d, o + 4)))
        o += 6
    return recs


def read_table(d, t):
    """([[(u, v, x, y, w, h)]], end): a sheet's lines, each a list of sprites."""
    count, o, lines = hw(d, t), t + 4, []
    for _ in range(count):
        n = hw(d, o)
        o += 2
        segs = []
        for _ in range(n):
            segs.append(struct.unpack_from("<6h", d, o))
            o += 12
        lines.append(segs)
    return lines, o


def read_all(d):
    return [read_table(d, t)[0] for t in TABLES]


def load_credits(path=ROOT / "data/credits.tsv"):
    out = {}
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if ln and not ln.startswith("#"):
            n, _, text = ln.partition("\t")
            out[int(n)] = text
    return out


def stream_tim(d, off):
    """(decoded TIM, tim fields, end of the stream in d)."""
    size = 0
    head, _ = lz.decompress(d, off + 4, size=20)
    q = 8 + struct.unpack_from("<I", head, 8)[0]
    head, _ = lz.decompress(d, off + 4, size=q + 12)
    size = q + struct.unpack_from("<I", head, q)[0]
    dec, end = lz.decompress(d, off + 4, size=size)
    return dec, timscan.parse(dec, 0), end


def draw_text(sheet, text, u, v, fnt):
    """Glyphs with the dialogue font's drop shadow, into a pixel array."""
    pen = u
    for ch in text:
        w, rows = fnt.glyphs[ch]
        for r, bits in enumerate(rows):
            for x in range(w):
                if bits & (0x80 >> x):
                    sheet[v + 2 + r, pen + x] = INK
                    if not (r < 11 and rows[r + 1] & (0x80 >> x)) and not sheet[v + 3 + r, pen + x]:
                        sheet[v + 3 + r, pen + x] = SHADOW
        pen += w + 1


def new_x(line, old_x, w):
    """Where a line goes: headings centred, a label or sub-heading stays, anything in the right part starts at its column."""
    if line in HEADINGS:
        return (320 - w) // 2
    if old_x > 48:
        return min(RIGHT_X, SCREEN_X_MAX - w)
    return old_x


def build(orig):
    """English STAFF.BIN, same size: new tables, sheets and x positions. Raises when a sheet or a stream's slot is full."""
    d = bytearray(orig)
    fnt, credits = font.Font(), load_credits()
    first = 0
    widths = {n: fnt.width(t) for n, t in credits.items()}
    for s, t in enumerate(TABLES):
        lines, end = read_table(orig, t)
        y = lines[0][0][3]  # every sprite's own y: the rows start below the screen
        sheet = np.zeros((256, 256), dtype=np.uint8)
        table = struct.pack("<hh", len(lines), hw(orig, t + 2))
        pens = [0] * (256 // ROW_H)  # next free u per row: each line takes the first row with room
        for i in range(len(lines)):
            text = credits[first + i]
            if not text:
                table += struct.pack("<h", 0)
                continue
            w = widths[first + i] + PAD
            row = next((r for r, pen in enumerate(pens) if pen + w <= 256), None)
            if row is None:
                raise OverflowError(f"sheet {s} is full at line {first + i}")
            draw_text(sheet, text, pens[row], row * ROW_H, fnt)
            table += struct.pack("<7h", 1, pens[row], row * ROW_H, 0, y, w, ROW_H)
            pens[row] += w + GAP
        if t + len(table) > end:
            raise OverflowError(f"table {s}: {len(table)} bytes, room for {end - t}")
        d[t:end] = table + bytes(end - t - len(table))
        first += len(lines)
        dec, tim, stream_end = stream_tim(orig, STREAMS[s])
        new = bytearray(dec)
        new[tim["pix"]:tim["end"]] = (sheet[:, ::2] | (sheet[:, 1::2] << 4)).tobytes()
        stream = lz.compress(bytes(new))
        slot = stream_end - STREAMS[s]
        if len(stream) > slot:
            raise OverflowError(f"sheet {s}: stream {len(stream)} bytes, slot {slot}")
        d[STREAMS[s]:stream_end] = stream + bytes(slot - len(stream))
    for n, (line, x, _dy) in enumerate(read_layout(orig)):
        struct.pack_into("<h", d, LAYOUT + n * 6 + 2, new_x(line, x, widths[line]))
    return bytes(d)


def strips(out):
    from PIL import Image, ImageDraw
    d = (ROOT / "work/tree/ESCA/PRG/STAFF.BIN").read_bytes()
    first = 0
    for s, lines in enumerate(read_all(d)):
        dec, t, _end = stream_tim(d, STREAMS[s])
        im = timscan.render(dec, t).convert("RGBA")
        cols, rows = 2, (len(lines) + 1) // 2
        sheet = Image.new("RGB", (cols * 420, rows * 36), (40, 40, 60))
        dr = ImageDraw.Draw(sheet)
        for i, segs in enumerate(lines):
            x, y = (i // rows) * 420, (i % rows) * 36
            dr.text((x + 2, y + 10), f"{first + i}", fill=(255, 255, 0))
            for u, v, sx, _sy, w, h in segs:
                piece = im.crop((u, v, u + w, v + h)).resize((w * 2, h * 2), Image.NEAREST)
                sheet.paste(piece, (x + 34 + sx * 2, y + 2), piece)
        first += len(lines)
        sheet.save(Path(out) / f"lines_{s}.png")


if __name__ == "__main__":
    Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
    strips(sys.argv[1])
