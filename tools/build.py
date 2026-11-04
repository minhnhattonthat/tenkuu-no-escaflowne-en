"""build.py: rebuild the disc from work/tree + work/layout.xml with mkpsxiso. Run tools/unpack.py first.

  python -X utf8 tools/build.py [--out build/escaflowne_en] [--shift N]

Writes OUT.bin (both tracks in one file) + OUT.cue. --shift N adds N empty sectors ahead of every file: a test that
the game finds its files by name, so a later file growing can't break it (docs/re/disc.md).
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom

MKPSXISO = ROOT / "tools/mkpsxiso/mkpsxiso-2.30-win64/mkpsxiso.exe"
FIRST_FILE = '<file name="SYSTEM.CNF"'


def shifted(xml, sectors):
    """layout.xml text with `sectors` empty sectors ahead of the first file."""
    assert xml.count(FIRST_FILE) == 1, "SYSTEM.CNF not found once in layout.xml"
    return xml.replace(FIRST_FILE, f'<dummy sectors="{sectors}" type="0"/>\n{FIRST_FILE}')


def build(out, shift=0):
    """Build out.bin + out.cue. mkpsxiso reads paths relative to work/, where layout.xml sits."""
    work = ROOT / "work"
    layout = work / "layout.xml"
    if not layout.is_file():
        sys.exit("no work/layout.xml: run tools/unpack.py")
    if shift:
        layout = work / f"layout_shift{shift}.xml"
        layout.write_text(shifted((work / "layout.xml").read_text(encoding="utf-8"), shift), encoding="utf-8")
    out = Path(out).resolve()
    out.parent.mkdir(exist_ok=True)
    subprocess.run([str(MKPSXISO), "-y", "-q", "-o", str(out.with_suffix(".bin")), "-c", str(out.with_suffix(".cue")),
                    str(layout)], cwd=work, check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "build" / "escaflowne_en"))
    ap.add_argument("--shift", type=int, default=0)
    a = ap.parse_args()
    check_rom.check()
    build(a.out, a.shift)
    print(Path(a.out).with_suffix(".bin"))
