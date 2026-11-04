"""build.py: build the disc with mkpsxiso. Run tools/unpack.py first.

  python -X utf8 tools/build.py [--marker] [--qa ID=TEXT]... [--out build/escaflowne_en]
  python -X utf8 tools/build.py --identity [--shift N] [--out OUT]

Writes OUT.bin (both tracks in one file) + OUT.cue, and OUT.vamap (old string address -> new, for warp_all.py). The
default build holds the hook, font and every `en` line (tools/insert.py); --marker has every line as its id and filler
and goes to build/escaflowne_marker. --identity rebuilds the untouched tree. --shift N adds N empty sectors ahead of
every file: a test that the game finds its files by name, so a later file growing can't break it (docs/re/disc.md).
"""
import argparse
import shutil
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


def build(out, shift=0, layout=None):
    """Build out.bin + out.cue. mkpsxiso reads paths relative to work/, where layout.xml sits."""
    work = ROOT / "work"
    layout = Path(layout or work / "layout.xml")
    if not layout.is_file():
        sys.exit("no work/layout.xml: run tools/unpack.py")
    if shift:
        src = layout.read_text(encoding="utf-8")
        layout = work / f"layout_shift{shift}.xml"
        layout.write_text(shifted(src, shift), encoding="utf-8")
    out = Path(out).resolve()
    out.parent.mkdir(exist_ok=True)
    subprocess.run([str(MKPSXISO), "-y", "-q", "-o", str(out.with_suffix(".bin")), "-c", str(out.with_suffix(".cue")),
                    str(layout)], cwd=work, check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    ap.add_argument("--shift", type=int, default=0)
    ap.add_argument("--identity", action="store_true")
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT")
    a = ap.parse_args()
    check_rom.check()
    out = Path(a.out or ROOT / "build" / ("escaflowne_marker" if a.marker else "escaflowne_en"))
    if a.identity:
        build(out, a.shift)
    else:
        import insert
        layout = insert.insert(mode="marker" if a.marker else "en", qa=dict(q.split("=", 1) for q in a.qa))
        build(out, a.shift, layout)
        shutil.copy(ROOT / "work/en/vamap.tsv", out.with_suffix(".vamap"))
    print(out.with_suffix(".bin"))
