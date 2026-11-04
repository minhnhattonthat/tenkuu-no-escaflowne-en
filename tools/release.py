"""release.py: build, gate, patch and verify; writes release/<name>.xdelta + .zip. It never publishes anything.

    python -X utf8 tools/release.py [--version 1.0] [--force]

Stops at the first failure: build, tests, smoke, jp_left, qa_gate on every work/qa/**/manifest.tsv, docs/polish.md, the
build matches the toured one (work/qa/tour.sha1), patch track 1, re-apply to the clean dump, boot the player's own files
(patched track 1, original track 2, original cue). The patch covers track 1 only, so the player keeps track 2 and the cue.
Refuses to overwrite a version's files without --force. The debug tool is a Lua probe (tools/debug), never in the image;
the plain build below takes neither --marker nor --qa.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import skill  # noqa: E402

SKILL = Path(skill.SKILL)
ROM = ROOT / "rom"
CUE = ROM / "Tenkuu no Escaflowne (Japan).cue"
TRACK1 = ROM / "Tenkuu no Escaflowne (Japan) (Track 1).bin"
TRACK2 = ROM / "Tenkuu no Escaflowne (Japan) (Track 2).bin"
BUILT = ROOT / "build/escaflowne_en.bin"
PLAYER = ROOT / "build/player"
NOTES = ROOT / "docs/release-readme.txt"


def run(*cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    if subprocess.call([str(c) for c in cmd], cwd=ROOT):
        sys.exit(f"release stopped: {cmd[1] if cmd[0] == sys.executable else cmd[0]} failed")


def py(*args):
    run(sys.executable, "-X", "utf8", *args)


def track1_size(cue_text):
    """Bytes before track 2 in a one-file cue: its first INDEX after TRACK 02, at 75 sectors a second."""
    m = re.search(r"TRACK 02.*?INDEX \d\d (\d\d):(\d\d):(\d\d)", cue_text, re.S)
    if not m:
        sys.exit("no track 2 in the build's cue")
    mins, secs, frames = map(int, m.groups())
    return ((mins * 60 + secs) * 75 + frames) * 2352


def open_polish(text):
    return [ln for ln in text.splitlines() if ln.lstrip().startswith("- [ ]")]


def digests(path):
    sha, md5, crc = hashlib.sha1(), hashlib.md5(), 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            sha.update(chunk)
            md5.update(chunk)
            crc = zlib.crc32(chunk, crc)
    return {"size": path.stat().st_size, "crc32": f"{crc:08x}", "md5": md5.hexdigest(), "sha1": sha.hexdigest()}


def gates():
    py("tools/build.py")
    py("tools/check.py")
    py(SKILL / "scripts/emu.py", "build/escaflowne_en.cue", "--out", "work/qa/release_smoke", "--route", "tools/routes/boot.txt", "--smoke")
    for f in [ROOT / "work/en/SLPS_010.15", *sorted((ROOT / "work/en/ESCA/PRG").iterdir())]:
        py(SKILL / "scripts/jp_left.py", f, "--sjis")
    manifests = sorted((ROOT / "work/qa").rglob("manifest.tsv"))
    if len(manifests) < 2:
        sys.exit("expected the visual tour and story pass manifests under work/qa")
    for man in manifests:
        py(SKILL / "scripts/qa_gate.py", "check", man, man.parent / "verdicts")
    left = open_polish((ROOT / "docs/polish.md").read_text(encoding="utf-8"))
    if left:
        sys.exit("docs/polish.md has open lines:\n" + "\n".join(left))
    toured = (ROOT / "work/qa/tour.sha1").read_text().split()[0]
    if toured != digests(BUILT)["sha1"]:
        sys.exit(f"this build isn't the one toured ({toured}): rerun the tour and qa_gate, then update work/qa/tour.sha1")


def make_patch(patch):
    """Split the built image at track 1's end, diff it against the clean dump, re-apply with a player's plain command."""
    size = track1_size((ROOT / "build/escaflowne_en.cue").read_text())
    if size != TRACK1.stat().st_size:
        sys.exit(f"built track 1 is {size} bytes, the dump's is {TRACK1.stat().st_size}")
    PLAYER.mkdir(exist_ok=True)
    new = PLAYER / "track1_en.bin"
    with open(BUILT, "rb") as src, open(new, "wb") as dst, open(TRACK2, "rb") as t2:
        left = size
        while left:
            left -= dst.write(src.read(min(1 << 20, left)))
        if hashlib.sha1(src.read()).digest() != hashlib.sha1(t2.read()).digest():
            sys.exit("the built track 2 differs from the dump's, but the patch leaves the player's track 2 alone")
    # -S djw: patchers built without lzma (Delta Patcher, old xdelta UIs) can read it. -B: moved files stay in reach.
    run(XDELTA, "-e", "-f", "-9", "-S", "djw", "-B", 1 << 30, "-s", TRACK1, new, patch)
    applied = PLAYER / TRACK1.name
    run(XDELTA, "-d", "-f", "-s", TRACK1, patch, applied)
    want, got = digests(new), digests(applied)
    if want["sha1"] != got["sha1"]:
        sys.exit(f"re-applied patch gives {got['sha1']}, expected {want['sha1']}")
    new.unlink()
    for f in (TRACK2, CUE):
        (PLAYER / f.name).unlink(missing_ok=True)
        os.link(f, PLAYER / f.name)
    py(SKILL / "scripts/emu.py", PLAYER / CUE.name, "--out", "work/qa/release_player", "--route", "tools/routes/boot.txt", "--smoke")
    return got


def make_zip(path, patch, patched, version):
    """ZIP_STORED: xdelta output is already compressed."""
    fields = {"version": version, "patch": patch.name, "patched_crc32": patched["crc32"], "patched_sha1": patched["sha1"]}
    for key, f in (("t1", TRACK1), ("t2", TRACK2)):
        fields |= {f"{key}_{k}": v for k, v in digests(f).items()}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.write(patch, patch.name)
        z.writestr("README.txt", NOTES.read_text(encoding="utf-8").format(**fields))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's release files")
    a = ap.parse_args()
    XDELTA = shutil.which("xdelta3") or sys.exit("xdelta3 not on PATH (github.com/jmacd/xdelta-gpl releases)")
    out = ROOT / "release"
    name = f"Tenkuu_no_Escaflowne_EN_v{a.version}"
    patch, archive = out / f"{name}.xdelta", out / f"{name}.zip"
    if not a.force and (patch.exists() or archive.exists()):
        sys.exit(f"{archive} exists: --force to replace it")
    out.mkdir(exist_ok=True)
    gates()
    patched = make_patch(patch)
    make_zip(archive, patch, patched, a.version)
    print(f"{archive}\npatched track 1: {patched['size']} bytes, CRC32 {patched['crc32']}, SHA-1 {patched['sha1']}")
    print(f"playable: {PLAYER / CUE.name}; publishing is the user's call")
