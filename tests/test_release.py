"""The two pieces of release.py that decide what ships: where track 1 ends and whether polish is finished."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import release  # noqa: E402

CUE = """FILE "x.bin" BINARY
  TRACK 01 MODE2/2352
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    INDEX 00 48:42:73
    INDEX 01 48:44:73
"""


def test_track1_ends_at_track2_index_00():
    assert release.track1_size(CUE) == 515612496  # the dump's Track 1, in bytes


def test_open_polish_lines():
    assert release.open_polish("- [x] a\n- [ ] b - note\ntext [ ]\n") == ["- [ ] b - note"]
