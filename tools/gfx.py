"""gfx.py: redraw the graphics text in English (docs/re/graphics.md rows 1-4), from the disc's own files.

    gfx.edited()                      {tree-relative path: new file bytes}, same size as the original
    python -X utf8 tools/gfx.py OUT   write each picture to OUT as a PNG, to check by eye

Every redraw keeps the TIM's header and draws with the palette it has; only a card's accent ramp gets brighter.
"""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import fmv  # noqa: E402
import font  # noqa: E402
import lz  # noqa: E402
import staff  # noqa: E402
import timscan  # noqa: E402

KUDO = "ESCA/TIM/KUDO"
SERIF = ROOT / "fonts/LiberationSerif-Bold.ttf"
DISPLAY = ROOT / "fonts/Cinzel-Variable.ttf"
SS = 4  # supersampling for antialiased lettering
# (chapter line, title rows, the word drawn in the card's accent colour, as the Japanese colours one kanji)
CARDS = {
    1: ("Chapter 1", ["Another World: Gaea"], "Another"),
    2: ("Chapter 2", ["The Mystic Moon"], "Moon"),
    3: ("Chapter 3", ["The Blue-Eyed Prince"], "Blue-Eyed"),
    4: ("Chapter 4", ["Paradise Lost"], "Paradise"),
    5: ("Chapter 5", ["Operation:", "Golden Rule of Love"], "Golden"),
    6: ("Chapter 6", ["Angel of Black Wings"], "Wings"),
    7: ("Chapter 7", ["Eternal Feelings"], "Eternal"),
}
HEAD_PX, TITLE_PX, MIN_PX = 24, 26, 15
LOGO_RECT = (0, 0, 240, 125)  # x0, y0, x1, y1: ESCA111's logo; the menu words below it stay
GLOW_OFFSET = (1, -3)  # rows, columns from the star's crossing to the glow's brightest point
LINE_PEAK, LINE_SLOPE, LINE_FLOOR = 232, 4, 40  # the hairlines' grey: at the glow, fall per pixel, at the far ends
LOGO_SPACING = 24  # px at the 200 px master, so F, L and O don't touch once squeezed into the logo's box
COPYRIGHT = "SUNRISE / TV TOKYO"
COPYRIGHT_TEXT_X = 18  # after the row's own (c) glyph
COPYRIGHT_END_X = 160
PLACEHOLDER = ("UNDER", "CONSTR-", "UCTION")
PLACEHOLDER_SRC = "ESCA/BG/00/MDAT01A.BIN"
PLACEHOLDER_OFFS = (0x38790, 0x3993C)  # stream starts, the 4-byte header included; docs/re/graphics.md row 6


def tree_bytes(rel):
    return (extract.TREE / rel).read_bytes()


def pixels(d, t):
    """An 8bpp TIM's pixels as an array that shares no memory with d."""
    return np.frombuffer(d, dtype=np.uint8, count=t["w"] * 2 * t["h"], offset=t["pix"]).reshape(t["h"], t["w"] * 2).copy()


def with_pixels(d, t, arr):
    out = bytearray(d)
    out[t["pix"]:t["end"]] = arr.tobytes()
    return bytes(out)


def rgb(v):
    return (v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8


def luma(v):
    r, g, b = rgb(v)
    return r * 0.3 + g * 0.59 + b * 0.11


def serif(px):
    return ImageFont.truetype(str(SERIF), px * SS)


def text_mask(text, f, width, height, x, y_mid):
    """Coverage 0-255 of text centred on (x, y_mid), and the x where each word starts."""
    im = Image.new("L", (width * SS, height * SS), 0)
    left = x * SS - f.getlength(text) / 2
    ImageDraw.Draw(im).text((left, y_mid * SS), text, font=f, fill=255, anchor="lm")
    return np.asarray(im.resize((width, height), Image.BOX), dtype=np.float32), left / SS


def ramp_of(pal, indices):
    return sorted(set(indices), key=lambda i: luma(pal[i]))


def card(n):
    """A chapter card: both rows redrawn at the centre the Japanese has, in its grey ramp and its accent ramp."""
    rel = f"{KUDO}/TI0{n}.TIM"
    d = tree_bytes(rel)
    t = timscan.parse(d, 0)
    old = pixels(d, t)
    pal = t["clut"]
    used = sorted(set(old.ravel().tolist()) - {0})
    grey = [i for i in used if max(rgb(pal[i])) - min(rgb(pal[i])) < 16]
    accent = [i for i in used if i not in grey] or grey
    grey, accent = ramp_of(pal, grey), ramp_of(pal, accent)
    bands, row = [], None
    for y in range(old.shape[0] + 1):
        ink = y < old.shape[0] and old[y].any()
        if ink and row is None:
            row = y
        elif not ink and row is not None:
            xs = np.nonzero(old[row:y].any(axis=0))[0]
            bands.append((row, y, int(xs[0]), int(xs[-1])))
            row = None
    bands = [b for b in bands if b[1] - b[0] > 6]
    head, titles, word = CARDS[n]
    assert len(bands) == len(titles) + 1, (n, bands)
    # some accents are too dark to read at the size English needs: brighten them in the card's own CLUT, hue kept
    d = bytearray(d)
    gain = max(1.0, 170 / max(luma(pal[i]) for i in accent))
    clut_at = t["off"] + 20
    for i in accent:
        r, g, b = [min(31, round(c / 8 * gain)) for c in rgb(pal[i])]
        struct.pack_into("<H", d, clut_at + i * 2, (pal[i] & 0x8000) | b << 10 | g << 5 | r)
    new = np.zeros_like(old)
    for (y0, y1, x0, x1), text, px in zip(bands, [head] + titles, [HEAD_PX] + [TITLE_PX] * len(titles)):
        cx = (x0 + x1) // 2
        room = 2 * min(cx, old.shape[1] - 1 - cx) - 2
        while serif(px).getlength(text) / SS > room:
            px -= 1
        if px < MIN_PX:
            raise ValueError(f"card {n}: {text!r} needs {px} px")
        f = serif(px)
        mask, left = text_mask(text, f, old.shape[1], old.shape[0], cx, (y0 + y1) / 2)
        a0, a1 = -1, -1
        if word in text and text is not head:
            a0 = left + f.getlength(text[:text.index(word)]) / SS
            a1 = a0 + f.getlength(word) / SS
        for y, x in zip(*np.nonzero(mask > 40)):
            ramp = accent if a0 <= x < a1 else grey
            new[y, x] = ramp[min(int(mask[y, x] / 256 * len(ramp)), len(ramp) - 1)]
    return rel, with_pixels(bytes(d), t, new)


def nearest(pal, used, colour):
    """The used palette index nearest a colour."""
    return min(used, key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb(pal[i]), colour)))


def logo(arr, pal):
    """ESCA111's logo: the sphere and star stay, English letters over them, each column coloured as the Japanese was there."""
    x0, y0, x1, y1 = LOGO_RECT
    old = arr[y0:y1, x0:x1]
    bg = int(old[0, 0])
    used = sorted(set(old.ravel().tolist()) - {bg})
    col = np.array([rgb(pal[i]) for i in range(256)], dtype=np.int32)
    spread = (col.max(axis=1) - col.min(axis=1))[old]
    neutral = (old != bg) & (spread < 24)
    lum = col.sum(axis=1) // 3
    # the star's two hairlines: the row and column holding most neutral pixels
    frow, fcol = int(neutral.sum(axis=1).argmax()), int(neutral.sum(axis=0).argmax())
    # the glow peaks just off their crossing (read from the brightness along each line); a black disc around it
    yy, xx = np.indices(old.shape)
    r = np.hypot(yy - frow - GLOW_OFFSET[0], xx - fcol - GLOW_OFFSET[1]).astype(int)
    radius = 23
    # per radius, the darkest neutral: the old letters and rays only ever add light, so that's the bare glow
    profile, last = {}, None
    for k in range(radius + 1):
        vals = lum[old[(r == k) & neutral]]
        darkest = int(old[(r == k) & neutral][vals.argmin()]) if vals.size else last
        last = darkest if last is None or lum[darkest] <= lum[last] else last
        profile[k] = last
    new = np.full_like(old, bg)
    # the disc wholly from the profile, then the hairlines over it: any pixel kept from the old art could be a letter's edge
    disc = r <= radius
    for y, x in zip(*np.nonzero(disc)):
        new[y, x] = profile[int(r[y, x])]
    greys = sorted(set(old[neutral].tolist()))

    def hairline(distance):
        want = max(LINE_FLOOR, LINE_PEAK - LINE_SLOPE * distance)
        return min(greys, key=lambda i: abs(int(lum[i]) - want))

    for x in range(1, old.shape[1] - 1):
        if old[frow, x] != bg:
            new[frow, x] = hairline(abs(x - fcol - GLOW_OFFSET[1]))
    for y in range(old.shape[0]):
        if old[y, fcol] != bg:
            new[y, fcol] = hairline(abs(y - frow - GLOW_OFFSET[0]))

    # column colours from the big letters, the outline from their brightest colour
    big = (old != bg) & ~neutral & (yy > 48) & (col[old][:, :, 2] > col[old][:, :, 0])
    outline = max((i for i in set(old[big].tolist())), key=lambda i: luma(pal[i]))
    colour_at = np.full(old.shape[1], -1, dtype=np.int32)
    for x in range(old.shape[1]):
        vals = old[:, x][big[:, x] & (old[:, x] != outline)]
        if vals.size:
            colour_at[x] = np.bincount(vals).argmax()
    have = np.nonzero(colour_at >= 0)[0]
    for x in range(old.shape[1]):
        colour_at[x] = colour_at[have[np.abs(have - x).argmin()]]

    def stamp(text, weight, cap_px, box, fill_of, edge=None, spacing=0):
        f = ImageFont.truetype(str(DISPLAY), 200)
        f.set_variation_by_axes([weight])
        im = Image.new("L", (int(f.getlength(text)) + spacing * len(text) + 40, 280), 0)
        pen = 20
        for ch in text:
            ImageDraw.Draw(im).text((pen, 10), ch, font=f, fill=255)
            pen += f.getlength(ch) + spacing
        im = im.crop(im.getbbox())
        bx0, by0, bx1, by1 = box
        im = im.resize((bx1 - bx0 - cap_px, by1 - by0), Image.LANCZOS)
        # the Japanese leans forward: a shear of cap_px across the height
        im = im.transform((bx1 - bx0, by1 - by0), Image.AFFINE, (1, cap_px / (by1 - by0), -cap_px, 0, 1, 0), Image.BICUBIC)
        m = np.asarray(im) > 128
        dil = m.copy()
        if edge is not None:
            dil[1:] |= m[:-1]
            dil[:-1] |= m[1:]
            dil[:, 1:] |= m[:, :-1]
            dil[:, :-1] |= m[:, 1:]
        for y, x in zip(*np.nonzero(dil)):
            new[by0 + y, bx0 + x] = fill_of(bx0 + x) if m[y, x] else edge

    red = nearest(pal, used, (248, 0, 40))
    stamp("THE VISION OF", 700, 3, (56, 20, 214, 38), lambda _x: red)
    stamp("ESCAFLOWNE", 700, 8, (6, 50, 234, 100), lambda x: int(colour_at[x]), outline, spacing=LOGO_SPACING)
    arr[y0:y1, x0:x1] = new


def copyright_row(arr, y0, y1):
    """The (c) glyph stays; the kanji row becomes the dialogue font, bold and tracked to fill the width."""
    row = arr[y0:y1, :COPYRIGHT_END_X]
    bg = int(np.bincount(row.ravel()).argmax())
    ink = int(np.bincount(row[row != bg]).argmax())
    fnt = font.Font()
    room = COPYRIGHT_END_X - COPYRIGHT_TEXT_X
    bold = sum(fnt.glyphs[c][0] + 2 for c in COPYRIGHT) - 1
    track = max(0, (room - bold) // (len(COPYRIGHT) - 1))
    row[:, COPYRIGHT_TEXT_X:] = bg
    pen = COPYRIGHT_TEXT_X
    top = (y1 - y0 - font.ROWS) // 2
    for ch in COPYRIGHT:
        w, rows = fnt.glyphs[ch]
        for r, bits in enumerate(rows):
            for x in range(w):
                if bits & (0x80 >> x):
                    row[top + r, pen + x] = ink
                    row[top + r, pen + x + 1] = ink
        pen += w + 2 + track
    if pen - track - 2 > COPYRIGHT_END_X:
        raise ValueError("copyright row too wide")


def first_ink_row(arr, y_from, x_end=COPYRIGHT_END_X):
    """The first of the rows from y_from where the art holds more than one colour."""
    for y in range(y_from, arr.shape[0]):
        if len(set(arr[y, :x_end].tolist())) > 1:
            return y
    raise ValueError("no ink")


def title_files():
    out = {}
    d = tree_bytes(f"{KUDO}/ESCA111.TIM")
    t = timscan.parse(d, 0)
    arr = pixels(d, t)
    logo(arr, t["clut"])
    copyright_row(arr, 161, 176)
    out[f"{KUDO}/ESCA111.TIM"] = with_pixels(d, t, arr)
    for n in ("ZZZZZ2", "ZZZZZ3"):
        d = tree_bytes(f"{KUDO}/{n}.TIM")
        t = timscan.parse(d, 0)
        arr = pixels(d, t)
        y = first_ink_row(arr, 150)
        copyright_row(arr, y, y + 15)
        out[f"{KUDO}/{n}.TIM"] = with_pixels(d, t, arr)
    return out


def placeholder_tim(dec, t):
    """The portrait-sized "under construction" picture: English, white letters with the Japanese's yellow edge."""
    old = pixels(dec, t)
    pal = t["clut"]
    bg = int(np.bincount(old.ravel()).argmax())
    white = max(range(256), key=lambda i: (rgb(pal[i])[2] > 200, luma(pal[i])) if i in set(old.ravel().tolist()) else (False, -1))
    yellow = int(np.bincount(old[(old != bg) & (old != white)]).argmax())
    new = np.full_like(old, bg)
    for (text, y) in zip(PLACEHOLDER, (44, 80, 116)):
        f = serif(22)
        m = text_mask(text, f, old.shape[1], old.shape[0], old.shape[1] // 2, y)[0] > 110
        grown = m.copy()
        grown[1:] |= m[:-1]
        grown[:-1] |= m[1:]
        grown[:, 1:] |= m[:, :-1]
        grown[:, :-1] |= m[:, 1:]
        new[grown] = yellow
        new[m] = white
    return with_pixels(dec, t, new)


def placeholder_files():
    """Every copy of the picture, in every MDAT: same stream start, shorter stream, zero padded, so no pointer moves.
    Found by the disc's exact stream bytes, one variant per VRAM page."""
    src = tree_bytes(PLACEHOLDER_SRC)
    variants = {}
    for off in PLACEHOLDER_OFFS:
        dec, t, end = staff.stream_tim(src, off)
        new = lz.compress(placeholder_tim(dec, t))
        if len(new) > end - off:
            raise OverflowError(f"placeholder stream {len(new)} bytes, slot {end - off}")
        variants[src[off:end]] = new + bytes(end - off - len(new))
    out = {}
    for path in sorted((extract.TREE / "ESCA/BG").rglob("MDAT*.BIN")):
        d = path.read_bytes()
        for old, new in variants.items():
            d = d.replace(old, new)
        if d != path.read_bytes():
            out[path.relative_to(extract.TREE).as_posix()] = d
    return out


def edited():
    out = title_files()
    out.update(placeholder_files())
    for n in CARDS:
        rel, data = card(n)
        out[rel] = data
    out["ESCA/PRG/STAFF.BIN"] = staff.build(tree_bytes("ESCA/PRG/STAFF.BIN"))
    out[fmv.TREE_PATH] = fmv.build()
    return out


def save_pngs(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    src = tree_bytes(PLACEHOLDER_SRC)
    dec, t, _end = staff.stream_tim(src, PLACEHOLDER_OFFS[0])
    im = timscan.render(placeholder_tim(dec, t), t).convert("RGB")
    im.save(out / "PLACEHOLDER.png")
    for rel, data in edited().items():
        name = Path(rel).stem
        if name.startswith("MDAT"):
            continue
        if rel.endswith(".TIM"):
            t = timscan.parse(data, 0)
            sheets = [(name, data, t)]
        else:
            sheets = [(f"{name}_{s}", *staff.stream_tim(data, off)[:2]) for s, off in enumerate(staff.STREAMS)]
        for label, d, t in sheets:
            im = timscan.render(d, t).convert("RGBA")
            bg = Image.new("RGBA", im.size, (60, 0, 60, 255))
            bg.alpha_composite(im)
            bg.save(out / f"{label}.png")


if __name__ == "__main__":
    save_pngs(sys.argv[1])
