"""fmv_sample.py OUT [--n 3]: decode N evenly spaced frames from every FMV on the disc with jPSXdec, and make sheets.
Needs tools/jpsxdec (github.com/m35/jpsxdec, v2.1) and an index at work/jp.idx (java -jar jpsxdec.jar -f BIN -x work/jp.idx)."""
import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "tools/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar"


def videos():
    for line in (ROOT / "work/jp.idx").read_text(encoding="utf-8", errors="replace").splitlines():
        if "Type:Video" in line:
            m = re.match(r"#:(\d+)\|ID:([^|]+)\|.*Frame Count:(\d+)", line)
            yield int(m[1]), m[2], int(m[3])


def grab(job):
    item, name, frame, out = job
    d = Path(out) / f"{item}_{frame}"
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["java", "-jar", str(JAR), "-x", "work/jp.idx", "-i", str(item), "-dir", str(d), "-vf", "png", "-noaud",
                    "-start", str(frame), "-end", str(frame), "-q", "low"], cwd=ROOT, capture_output=True, timeout=300)
    pngs = list(d.rglob("*.png"))
    return (name, frame, pngs[0] if pngs else None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    jobs = []
    for item, name, count in videos():
        for k in range(a.n):
            jobs.append((item, name, int((k + 0.5) * count / a.n), a.out))
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(grab, jobs))
    missing = [r[:2] for r in res if r[2] is None]
    print(len(res), "frames,", len(missing), "failed", missing[:5])
    cols, tw, th = 8, 160, 132
    per = cols * 8
    good = [r for r in res if r[2]]
    for s in range(0, len(good), per):
        chunk = good[s:s + per]
        S = Image.new("RGB", (cols * tw, ((len(chunk) + cols - 1) // cols) * th), (60, 0, 60))
        dr = ImageDraw.Draw(S)
        for i, (name, frame, p) in enumerate(chunk):
            x, y = (i % cols) * tw, (i // cols) * th
            S.paste(Image.open(p).convert("RGB").resize((tw, th - 12)), (x, y + 12))
            dr.text((x + 1, y), f"{Path(name).name[:8]} {frame}", fill=(255, 255, 0))
        S.save(Path(a.out) / f"fmv_{s // per:02d}.png")
    print("sheets in", a.out)
