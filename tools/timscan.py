"""timscan.py: find TIM images in disc files and render them. Read-only on the tree.

  timscan.py list FILE..                       one line per TIM: file, offset, bpp, size, clut, vram pos
  timscan.py sheet OUTDIR FILE.. [--per N]     numbered contact sheets + OUTDIR/index.tsv (every TIM, none dropped)
  timscan.py one FILE OFF OUT.png [--clut N] [--zoom Z]
"""
import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw


def parse(d, o):
    """Return dict for a TIM at d[o:], or None. Validates sizes so pixel data rarely passes."""
    if o + 8 > len(d) or d[o:o + 4] != b"\x10\0\0\0":
        return None
    fl = struct.unpack_from("<I", d, o + 4)[0]
    if fl & ~0xF or (fl & 7) > 3:
        return None
    t = {"off": o, "bpp": fl & 7, "clut": None, "cx": 0, "cy": 0}
    p = o + 8
    if fl & 8:
        if p + 12 > len(d):
            return None
        ln, cx, cy, cw, ch = struct.unpack_from("<IHHHH", d, p)
        if ln != 12 + cw * ch * 2 or not cw or not ch or cx >= 1024 or cy >= 512 or p + ln > len(d):
            return None
        t["clut"] = struct.unpack_from("<%dH" % (cw * ch), d, p + 12)
        t.update(cw=cw, ch=ch, cx=cx, cy=cy)
        p += ln
    if p + 12 > len(d):
        return None
    ln, x, y, w, h = struct.unpack_from("<IHHHH", d, p)
    if ln != 12 + w * h * 2 or not w or not h or x >= 1024 or y >= 512 or p + ln > len(d):
        return None
    t.update(x=x, y=y, w=w, h=h, pix=p + 12, end=p + ln)
    return t


def scan(d):
    out, o = [], 0
    while True:
        o = d.find(b"\x10\0\0\0", o)
        if o < 0:
            return out
        t = parse(d, o)
        if t:
            out.append(t)
            o = t["end"]
        else:
            o += 1


def scan_lz(d):
    """Find LZ-compressed TIMs: flag byte + 10 00 00 00 + TIM flag literal. Returns (stream_offset, decoded, tim)."""
    import re
    import lz
    found, pos = [], 0
    pat = re.compile(rb"[\x00-\x1f]\x10\x00\x00\x00[\x00\x01\x02\x08\x09]", re.S)
    while True:
        m = pat.search(d, pos)
        if not m:
            return found
        pos = m.start() + 1
        try:
            head, _ = lz.decompress(d, m.start(), limit=64, size=20 + 12)
            if head[:4] != b"\x10\0\0\0" or len(head) < 32:
                continue
            fl = head[4]
            q = 8
            if fl & 8:
                q += struct.unpack_from("<I", head, 8)[0]
            if q > 0x20000:
                continue
            head, _ = lz.decompress(d, m.start(), limit=q + 64, size=q + 12)
            ln = struct.unpack_from("<I", head, q)[0]
            if ln > 0x100000 or ln < 12:
                continue
            out, end = lz.decompress(d, m.start(), size=q + ln)
        except (ValueError, struct.error, IndexError):
            continue
        t = parse(out, 0)
        if t and t["end"] == len(out):
            found.append((m.start(), out, t))
            pos = end


def col(v):
    return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31, 0 if v == 0 else 255)


def render(d, t, clut=0):
    w, h, p = t["w"], t["h"], t["pix"]
    b = t["bpp"]
    if b == 2:
        im = Image.new("RGBA", (w, h))
        px = struct.unpack_from("<%dH" % (w * h), d, p)
        im.putdata([col(v) for v in px])
        return im
    pal = t["clut"]
    if pal is None:
        pal = [(i * 0x0421) & 0x7FFF for i in range(32)] * 8
    if b == 0:
        n = 16
        base = clut * 16
        im = Image.new("RGBA", (w * 4, h))
        data = []
        for i in range(w * h * 2):
            v = d[p + i]
            data += [col(pal[(base + (v & 15)) % len(pal)]), col(pal[(base + (v >> 4)) % len(pal)])]
        im.putdata(data)
        return im
    if b == 1:
        base = clut * 256
        im = Image.new("RGBA", (w * 2, h))
        im.putdata([col(pal[(base + d[p + i]) % len(pal)]) for i in range(w * h * 2)])
        return im
    raise ValueError("24bpp not handled")


def sheet(outdir, files, per, maxw=1400, tile=320):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    idx = (outdir / "index.tsv").open("w", encoding="utf-8", newline="\n")
    idx.write("id\tfile\toffset\tbpp\tw\th\tvram\tclut_at\tsheet\n")
    items, n = [], 0

    def flush():
        nonlocal items
        if not items:
            return
        cols = maxw // tile
        rows = (len(items) + cols - 1) // cols
        S = Image.new("RGB", (cols * tile, rows * (tile + 12)), (60, 0, 60))
        dr = ImageDraw.Draw(S)
        for i, (tid, im) in enumerate(items):
            x, y = (i % cols) * tile, (i // cols) * (tile + 12)
            im = im.convert("RGBA")
            k = min(1, (tile - 2) / im.width, (tile - 2) / im.height)
            if k < 1:
                im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))))
            S.paste(im, (x, y + 12), im)
            dr.text((x + 1, y), tid, fill=(255, 255, 0))
        S.save(outdir / f"sheet_{flush.k:03d}.png")
        flush.k += 1
        items = []

    flush.k = 0
    for f in files:
        d = Path(f).read_bytes()
        for t in scan(d):
            tid = "T%05d" % n
            n += 1
            idx.write(f"{tid}\t{f}\t{t['off']:X}\t{t['bpp']}\t{t['w']}\t{t['h']}\t{t['x']},{t['y']}\t{t['cx']},{t['cy']}\tsheet_{flush.k:03d}\n")
            try:
                items.append((tid + " " + Path(f).name[:10] + " %X" % t["off"], render(d, t)))
            except Exception as e:
                print("skip", f, hex(t["off"]), e)
            if len(items) >= per:
                flush()
    flush()
    idx.close()
    print(n, "TIMs,", flush.k, "sheets in", outdir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="+")
    ap.add_argument("--per", type=int, default=20)
    ap.add_argument("--clut", type=int, default=0)
    ap.add_argument("--zoom", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "list":
        for f in a.args:
            d = Path(f).read_bytes()
            for t in scan(d):
                print(f"{f}\t{t['off']:X}\tbpp{t['bpp']}\t{t['w']}x{t['h']}\tvram {t['x']},{t['y']}\tclut {t['cx']},{t['cy']}")
    elif a.cmd == "sheet":
        sheet(a.args[0], a.args[1:], a.per)
    else:
        f, off, out = a.args
        d = Path(f).read_bytes()
        t = parse(d, int(off, 16))
        im = render(d, t, a.clut).convert("RGBA")
        bg = Image.new("RGBA", im.size, (60, 0, 60, 255))
        bg.alpha_composite(im)
        bg.resize((im.width * a.zoom, im.height * a.zoom), Image.NEAREST).save(out)
