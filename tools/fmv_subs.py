"""fmv_subs.py: burn English subtitles into the voiced videos, from data/fmv_subs.tsv (docs/re/fmv-subs.md).

    python -X utf8 tools/fmv_subs.py [SC02 ...]    rebuild work/fmv/subs/<video>.STR and print the frames replaced

The tsv's columns: video, start and end in seconds of the video's audio, Japanese as heard, English. jPSXdec re-encodes only
the frames under a line, in place, so each file keeps its size and the audio its timing. Cached per video.
"""
import csv
import hashlib
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "tools/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar"
TSV = ROOT / "data/fmv_subs.tsv"
OUT = ROOT / "work/fmv/subs"
STR_DIR = "ESCA/STR"
FPS = 150 / 10.01  # 2x disc speed is 150 sectors a second; every video's index says 1001/100 sectors a frame
FONT = ImageFont.truetype(str(ROOT / "fonts/LiberationSerif-Bold.ttf"), 15)
MAX_W, LINE_H, BOTTOM = 296, 16, 226  # px on the 320x240 frame; consumer CRTs can hide about 8 lines, so the last row clears 12
JOBS = 6


def load():
    """{video: [(start, end, english)]} in file order."""
    subs = {}
    with TSV.open(encoding="utf-8", newline="") as f:
        for video, start, end, _ja, en in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            subs.setdefault(video, []).append((float(start), float(end), en))
    return subs


def wrap(text):
    """The text as 1 or 2 rows inside MAX_W, split where the rows come closest to even."""
    if FONT.getlength(text) <= MAX_W:
        return [text]
    words = text.split()
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    rows = min(splits, key=lambda s: max(FONT.getlength(s[0]), FONT.getlength(s[1])), default=(text, ""))
    if max(FONT.getlength(r) for r in rows) > MAX_W:
        raise ValueError(f"subtitle needs 3 rows: {text}")
    return list(rows)


def burn(img, text):
    """White text with a black edge, which stays readable on any frame and survives MDEC's blur."""
    draw = ImageDraw.Draw(img)
    rows = wrap(text)
    for n, row in enumerate(rows):
        y = BOTTOM - LINE_H * (len(rows) - n)
        draw.text(((320 - FONT.getlength(row)) / 2, y), row, font=FONT, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))


def frames_of(start, end):
    """The frame numbers a line stays up for."""
    return range(int(start * FPS), int(end * FPS) + 1)


def source(video):
    return next((ROOT / "work/tree" / STR_DIR).rglob(f"{video}.STR"))


def key(video, rows):
    h = hashlib.sha1(Path(__file__).read_bytes())
    h.update(repr(rows).encode())
    h.update(source(video).read_bytes())
    return h.hexdigest()


def java(*args, cwd):
    p = subprocess.run(["java", "-jar", str(JAR), *map(str, args)], cwd=cwd, check=True, capture_output=True, text=True, errors="replace")
    return p.stdout + p.stderr


def build(video, rows):
    """The subtitled video's bytes, rebuilt only when this file, its lines or the source change."""
    done, stamp = OUT / f"{video}.STR", OUT / f"{video}.key"
    if done.exists() and stamp.exists() and stamp.read_text() == key(video, rows):
        return done.read_bytes()
    work = OUT / f"{video}.work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "dec").mkdir(parents=True)
    src = source(video)
    shutil.copyfile(src, work / "v.STR")
    java("-f", "v.STR", "-x", "v.idx", cwd=work)
    wanted = {i: en for start, end, en in rows for i in frames_of(start, end)}
    java("-x", "v.idx", "-i", 0, "-dir", "dec", "-vf", "png", "-noaud", "-start", min(wanted), "-end", max(wanted), "-q", "high", cwd=work)
    decoded = {int(p.stem.rsplit("[", 1)[1].rstrip("]")): p for p in (work / "dec").glob("*.png")}
    lines = []
    for i, en in sorted(wanted.items()):
        if i not in decoded:  # the audio can outlast the last picture
            continue
        img = Image.open(decoded[i]).convert("RGB")
        burn(img, en)
        img.save(work / f"n{i:05d}.png")
        lines.append(f'  <replace frame="{i}">n{i:05d}.png</replace>')
    (work / "r.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<str-replace version="0.3">\n' + "\n".join(lines) + "\n</str-replace>\n")
    log = java("-x", "v.idx", "-i", 0, "-replaceframes", "r.xml", cwd=work)
    (OUT / f"{video}.log").write_text(log, encoding="utf-8")
    assert (work / "v.STR").stat().st_size == src.stat().st_size
    shutil.move(work / "v.STR", done)
    stamp.write_text(key(video, rows))
    shutil.rmtree(work)
    print(f"{video}: {len(lines)} frames", flush=True)
    return done.read_bytes()


def edited(only=None):
    """{tree-relative path: new bytes} for every subtitled video."""
    OUT.mkdir(parents=True, exist_ok=True)
    subs = {v: r for v, r in load().items() if not only or v in only}
    with ThreadPoolExecutor(JOBS) as pool:
        built = pool.map(lambda v: build(v, subs[v]), subs)
        return {source(v).relative_to(ROOT / "work/tree").as_posix(): b for v, b in zip(subs, built)}


if __name__ == "__main__":
    edited(sys.argv[1:])
