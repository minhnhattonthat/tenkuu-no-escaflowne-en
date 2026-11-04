"""unpack.py: extract the original disc to work/tree + work/layout.xml with dumpsxiso (read-only on rom/)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom

DUMPSXISO = ROOT / "tools/mkpsxiso/mkpsxiso-2.30-win64/dumpsxiso.exe"
CUE = "rom/Tenkuu no Escaflowne (Japan).cue"

if __name__ == "__main__":
    check_rom.check()
    (ROOT / "work").mkdir(exist_ok=True)
    sys.exit(subprocess.call([str(DUMPSXISO), "-x", "work/tree", "-s", "work/layout.xml", CUE], cwd=ROOT))
