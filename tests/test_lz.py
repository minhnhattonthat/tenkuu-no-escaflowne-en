"""LZ decoder and TIM scanner on hand-built streams, plus a real block when the unpacked disc is present."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lz
import sjis_scan
import timscan


def test_literals_and_overlapping_ref():
    # flags 0b00100000: two literals, one ref, then literals; ref v=0x0401: len (1)+3=4, dist 2 (overlaps its own output)
    stream = bytes([0b00100000]) + b"AB" + struct.pack("<H", 0x0401) + b"C"
    out, end = lz.decompress(stream, size=7)
    assert out == b"ABABABC"
    assert end == len(stream)


def test_ref_before_start_is_refused():
    with pytest.raises(ValueError):
        lz.decompress(bytes([0x80]) + struct.pack("<H", 5))


def test_timscan_finds_lz_tim():
    pix = bytes(range(32)) * 2
    tim = struct.pack("<II", 0x10, 2) + struct.pack("<IHHHH", 12 + len(pix), 0, 0, 8, 4) + pix
    # all-literal stream: a zero flag byte before each 8 literals
    s = b"".join(bytes([0]) + tim[i:i + 8] for i in range(0, len(tim), 8))
    found = timscan.scan_lz(b"\xff" * 3 + s + b"\xff" * 3)
    assert len(found) == 1 and found[0][0] == 3 and found[0][1] == tim


def test_sjis_runs_need_kana():
    d = b"\0" + "カード".encode("cp932") + b"\0" + "漢字漢字".encode("cp932") + b"\0"
    assert [t for _, t in sjis_scan.runs(d, 2)] == ["カード"]


TIM_BLOCK = ROOT / "work/tree/ESCA/BATTLE/ACT1/BATI11.BIN"


@pytest.mark.skipif(not TIM_BLOCK.is_file(), reason="disc not unpacked")
def test_real_block_decodes_to_declared_size():
    found = timscan.scan_lz(TIM_BLOCK.read_bytes())
    assert len(found) == 11
    assert found[0][0] == 0x40 and found[0][2]["w"] == 64 and found[0][2]["h"] == 256
