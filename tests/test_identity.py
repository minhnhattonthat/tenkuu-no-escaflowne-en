"""Identity build: the unedited tree rebuilds to the exact dump, and no program file issues a CD audio command."""
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
import cdcalls

TREE = ROOT / "work" / "tree"
LAYOUT = ROOT / "work" / "layout.xml"
TRACK1 = ROOT / "rom" / "Tenkuu no Escaflowne (Japan) (Track 1).bin"
TRACK2 = ROOT / "rom" / "Tenkuu no Escaflowne (Japan) (Track 2).bin"

needs_tree = pytest.mark.skipif(not (LAYOUT.is_file() and TREE.is_dir() and TRACK1.is_file()), reason="no dump or tree")


def _sha1(f, n):
    h = hashlib.sha1()
    while n:
        chunk = f.read(min(n, 1 << 20))
        assert chunk, "image is short"
        h.update(chunk)
        n -= len(chunk)
    return h.hexdigest()


def _sha1_of(path):
    with open(path, "rb") as f:
        return _sha1(f, path.stat().st_size)


@needs_tree
def test_rebuild_is_identical(tmp_path):
    # work/tree must stay the pristine unpack: English goes in a copy, or this fails.
    build.build(tmp_path / "id")
    out = tmp_path / "id.bin"
    size1, size2 = TRACK1.stat().st_size, TRACK2.stat().st_size
    try:
        assert out.stat().st_size == size1 + size2
        with open(out, "rb") as f:
            assert _sha1(f, size1) == _sha1_of(TRACK1)
            assert _sha1(f, size2) == _sha1_of(TRACK2)
    finally:
        out.unlink()  # 548 MB; pytest keeps its last three tmp dirs


def test_shift_adds_one_dummy_ahead_of_first_file():
    xml = '<directory_tree>\n  <file name="SYSTEM.CNF" type="data"/>\n  <file name="X"/>\n</directory_tree>'
    got = build.shifted(xml, 7)
    assert got.index('<dummy sectors="7"') < got.index('name="SYSTEM.CNF"')
    assert got.count("<dummy") == 1
    with pytest.raises(AssertionError):
        build.shifted("<directory_tree/>", 7)


def test_calls_reads_the_command_before_or_in_delay_slot():
    jal = (0x0C000000 | ((0x8005E048 & 0x0FFFFFFF) >> 2)).to_bytes(4, "little")
    li_a0_2 = (0x24040002).to_bytes(4, "little")
    nop = bytes(4)
    assert [c for _, _, c in cdcalls.calls(li_a0_2 + jal + nop)] == [2]
    assert [c for _, _, c in cdcalls.calls(nop + jal + li_a0_2)] == [2]
    assert [c for _, _, c in cdcalls.calls(nop + jal + nop)] == [None]


@needs_tree
def test_no_cd_audio_commands():
    """CdlPlay/GetTN/GetTD would tie the game to track 2's position; none exist, so track 1 may grow freely."""
    progs = [TREE / "SLPS_010.15"] + sorted((TREE / "ESCA" / "PRG").glob("*.BIN"))
    assert len(progs) > 10
    for p in progs:
        for i, _, cmd in cdcalls.calls(p.read_bytes()):
            assert cmd is not None, f"{p.name} word {i:#x}: command not an immediate, read it by hand"
            assert cmd not in (3, 0x13, 0x14), f"{p.name} word {i:#x}: command {cmd:#x}"
