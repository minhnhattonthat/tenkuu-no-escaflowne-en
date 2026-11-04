"""fmv.py: the opening video's title logo in English. SC01.STR is the only video with text (docs/re/graphics.md).

    python -X utf8 tools/fmv.py        rebuild work/fmv/SC01.STR and print the frames it replaced

The Japanese logo fades in over a panning star field, holds, then fades out as Hitomi walks through it. In each frame,
pixels brighter than a pan-aligned plate made before the logo appears are the old letters and take the plate's pixels;
then the new letters go on at the old logo's opacity. jPSXdec re-encodes those frames in place, so the file keeps its size
and the audio its timing. The result is cached by this file's hash.
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "tools/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar"
SOURCE = ROOT / "work/tree/ESCA/STR/00/SC01.STR"
OUT = ROOT / "work/fmv"
FONT = ROOT / "fonts/Cinzel-Variable.ttf"
TREE_PATH = "ESCA/STR/00/SC01.STR"

DECODE_LAST = 165
PLATE_FRAMES = (30, 38, 46, 52, 58)  # before the logo; their median loses most of the figure, who moves against the stars
FADE_IN = (66, 88)  # first and last frame of the old logo's fade, read off a sheet of the frames
FADE_OUT = (126, 148)
BOX = (15, 40, 305, 176)  # x0, y0, x1, y1: the old logo. Below it to the right is its (c) 1996 SUNRISE line, in English
GLARE_X_END, GLARE_Y_END = 182, 206  # the glare's stub under the box, left of that line
KANJI_X_END, KANJI_Y_END = 200, 104  # the red kanji end here; Hitomi, also warm, stays right of and below them
WALKS_IN_FRONT = 135  # from this frame she's drawn over the fading logo
MARGIN = 10  # rows at the plate's edges not to trust
KEY = 14  # brighter than the plate by this much counts as logo


def java(*args, cwd):
    subprocess.run(["java", "-jar", str(JAR), *map(str, args)], cwd=cwd, check=True, capture_output=True)


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def track(frames, first):
    """(dx, dy) per frame: the pan against frame `first`, followed outward from it, judged outside the logo's box."""
    ref = frames[first].mean(axis=2)
    keep = np.zeros(ref.shape, bool)
    keep[6:36, 40:] = True
    keep[190:234, 8:150] = True

    def best(i, start):
        cur = frames[i].mean(axis=2)
        scored = []
        for dy in range(start[1] - 2, start[1] + 3):
            for dx in range(start[0] - 2, start[0] + 3):
                scored.append((np.abs(ref - np.roll(cur, (-dy, -dx), (0, 1)))[keep].mean(), dx, dy))
        return min(scored)[1:]

    shifts = {first: (0, 0)}
    for i in range(first + 1, max(frames) + 1):
        shifts[i] = best(i, shifts[i - 1])
    for i in range(first - 1, min(frames) - 1, -1):
        shifts[i] = best(i, shifts[i + 1])
    return shifts


def moved(a, shift):
    return np.roll(a, shift[::-1], (0, 1))


def lettering():
    """(alpha, colour) on a 320x240 canvas: the words where the old ones stood, leaning as they did."""
    alpha = Image.new("L", (320, 240), 0)
    colour = np.zeros((240, 320, 3), dtype=np.float32)

    def stamp(text, box, lean, top, bottom):
        x0, y0, x1, y1 = box
        f = ImageFont.truetype(str(FONT), 200)
        f.set_variation_by_axes([700])
        im = Image.new("L", (int(f.getlength(text)) + 40, 280), 0)
        ImageDraw.Draw(im).text((20, 10), text, font=f, fill=255)
        im = im.crop(im.getbbox()).resize(((x1 - x0 - lean) * 2, (y1 - y0) * 2), Image.LANCZOS)
        h = (y1 - y0) * 2
        im = im.transform(((x1 - x0) * 2, h), Image.AFFINE, (1, lean * 2 / h, -lean * 2, 0, 1, 0), Image.BICUBIC)
        alpha.paste(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
        ramp = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
        colour[y0:y1, x0:x1] = np.array(top, dtype=np.float32) * (1 - ramp) + np.array(bottom, dtype=np.float32) * ramp

    stamp("THE VISION OF", (84, 54, 236, 76), 3, (255, 90, 110), (215, 20, 60))
    stamp("ESCAFLOWNE", (26, 86, 294, 136), 10, (250, 250, 255), (90, 120, 240))
    # a thin dark edge keeps the letters off the stars
    shade = np.asarray(alpha.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255
    return np.asarray(alpha, dtype=np.float32) / 255, colour, shade


def opacity(i):
    """The old logo's strength at frame i, read off the original fades (work/qa/cmp sheets of frames 52-154)."""
    if i <= FADE_IN[0] or i >= FADE_OUT[1]:
        return 0.0
    if i < FADE_IN[1]:
        return (i - FADE_IN[0]) / (FADE_IN[1] - FADE_IN[0])
    if i > FADE_OUT[0]:
        return (FADE_OUT[1] - i) / (FADE_OUT[1] - FADE_OUT[0])
    return 1.0


def compose(frames):
    """{frame: RGB image} for every frame the old logo shows in."""
    shifts = track(frames, PLATE_FRAMES[-1])
    plate = np.median([moved(frames[i], tuple(-v for v in shifts[i])) for i in PLATE_FRAMES], axis=0).astype(np.float32)
    alpha, colour, shade = lettering()
    yy, xx = np.indices(plate.shape[:2])
    x0, y0, x1, y1 = BOX
    region = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    region |= (xx >= x0) & (xx < GLARE_X_END) & (yy >= y1) & (yy < GLARE_Y_END)  # the old logo's glare runs below it
    held = np.mean([frames[i] - moved(plate, shifts[i]) for i in range(FADE_IN[1] + 12, FADE_OUT[0])], axis=0)
    shape = ((held.max(axis=2) > 40) & region).astype(np.uint8) * 255
    letters = np.asarray(Image.fromarray(shape).filter(ImageFilter.MaxFilter(11))) > 0  # room for the logo's slow drift
    out = {}
    for i, f in frames.items():
        o = opacity(i)
        if not o:
            continue
        back = moved(plate, shifts[i])
        diff = f - back
        # where the frame is brighter than the stars behind it, it's the old logo: unless it's Hitomi, warm and in front
        lit = diff.max(axis=2) > KEY
        if i < WALKS_IN_FRONT:
            logo = lit & region & ~((f[..., 0] > f[..., 2] + 30) & (xx > KANJI_X_END))
        else:  # she's in front now, tan and white: only blue pixels or saturated red near the old letters go
            kanji = (f[..., 0] > 1.6 * f[..., 1]) & (xx < KANJI_X_END) & (yy < KANJI_Y_END)
            logo = lit & letters & ((diff[..., 2] > diff[..., 0] + 6) | kanji)
        logo &= yy > max(shifts[i][1], 0) + MARGIN  # the plate has nothing above its own top edge, once it has panned down
        logo &= yy < plate.shape[0] - MARGIN + min(shifts[i][1], 0)
        grown = Image.fromarray(logo.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
        take = np.asarray(grown, dtype=np.float32)[..., None] / 255
        clean = f * (1 - take) + back * take
        a = (alpha * o)[..., None]
        s = (shade * o * 0.75)[..., None]
        img = clean * (1 - s) + 0 * s
        img = img * (1 - a) + colour * a
        out[i] = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return out


def key():
    h = hashlib.sha1(Path(__file__).read_bytes())
    h.update(SOURCE.read_bytes()[:2336 * 2000])
    return h.hexdigest()


def build():
    """The English SC01.STR's bytes, rebuilt only when this file or the source changes."""
    done, stamp_file = OUT / "SC01.STR", OUT / "SC01.key"
    if done.exists() and stamp_file.exists() and stamp_file.read_text() == key():
        return done.read_bytes()
    work = OUT / "work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "dec").mkdir(parents=True)
    shutil.copyfile(SOURCE, work / "SC01.STR")
    java("-f", "SC01.STR", "-x", "sc01.idx", cwd=work)
    java("-x", "sc01.idx", "-i", 0, "-dir", "dec", "-vf", "png", "-noaud", "-start", 0, "-end", DECODE_LAST, "-q", "high", cwd=work)
    frames = {}
    for p in sorted((work / "dec").glob("*.png")):
        frames[int(p.stem.rsplit("[", 1)[1].rstrip("]"))] = load(p)
    new = compose({i: f for i, f in frames.items() if i >= PLATE_FRAMES[0]})
    rows = []
    for i, img in sorted(new.items()):
        img.save(work / f"n{i:04d}.png")
        rows.append(f'  <replace frame="{i}">n{i:04d}.png</replace>')
    (work / "r.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<str-replace version="0.3">\n' + "\n".join(rows) + "\n</str-replace>\n")
    java("-x", "sc01.idx", "-i", 0, "-replaceframes", "r.xml", cwd=work)
    assert (work / "SC01.STR").stat().st_size == SOURCE.stat().st_size
    shutil.move(work / "SC01.STR", done)
    stamp_file.write_text(key())
    print(f"SC01.STR: {len(new)} frames, {min(new)}-{max(new)}")
    return done.read_bytes()


if __name__ == "__main__":
    build()
    sys.exit(0)
