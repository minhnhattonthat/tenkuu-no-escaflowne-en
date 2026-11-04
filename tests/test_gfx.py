"""The English graphics change only what they mean to, and the game's own decompressor reads the new staff roll."""
import struct
import sys
from pathlib import Path

import numpy as np
import pytest
import unicorn as uc
from unicorn import UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS32
from unicorn.mips_const import UC_MIPS_REG_29, UC_MIPS_REG_31, UC_MIPS_REG_4, UC_MIPS_REG_5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import font  # noqa: E402
import gfx  # noqa: E402
import lz  # noqa: E402
import staff  # noqa: E402
import timscan  # noqa: E402

needs_tree = pytest.mark.skipif(not (extract.TREE / "SLPS_010.15").is_file(), reason="no unpacked tree")
DECOMPRESS, EXE_BASE, STOP = 0x800157CC, 0x8000F800, 0x80001000
SRC, DST, PHYS = 0x80100000, 0x80140000, 0x1FFFFFFF
KUDO = extract.TREE / gfx.KUDO


@pytest.fixture(scope="module")
def edited():
    return gfx.edited()


def game_decompress(stream, size):
    """Run the disc's 0x800157CC under unicorn: an encoder test that doesn't trust our own decoder."""
    m = uc.Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    m.mem_map(0, 0x200000)
    m.mem_write(EXE_BASE & PHYS, (extract.TREE / "SLPS_010.15").read_bytes())
    m.mem_write(SRC & PHYS, stream)
    m.reg_write(UC_MIPS_REG_4, SRC)
    m.reg_write(UC_MIPS_REG_5, DST)
    m.reg_write(UC_MIPS_REG_29, 0x801F0000)
    m.reg_write(UC_MIPS_REG_31, STOP)
    m.emu_start(DECOMPRESS, STOP, count=40_000_000)
    return bytes(m.mem_read(DST & PHYS, size))


def test_compress_roundtrips_through_our_decoder():
    for data in (b"", b"a", b"abc" * 500, bytes(range(256)) * 8, bytes(5000), b"ab" + bytes(2000) + b"cd"):
        out, end = lz.decompress(lz.compress(data), 4, size=len(data))
        assert out == data
        assert end == len(lz.compress(data))


@needs_tree
def test_game_decompressor_reads_our_stream():
    data = bytes(range(256)) * 4 + bytes(3000) + b"credits" * 90
    assert game_decompress(lz.compress(data), len(data)) == data


@needs_tree
def test_game_decompressor_reads_the_new_staff_sheets(edited):
    new = edited["ESCA/PRG/STAFF.BIN"]
    for off in staff.STREAMS:
        dec, _t, end = staff.stream_tim(new, off)
        assert game_decompress(new[off:end], len(dec)) == dec


@needs_tree
def test_staff_changes_only_tables_streams_and_layout_x(edited):
    orig, new = (extract.TREE / "ESCA/PRG/STAFF.BIN").read_bytes(), edited["ESCA/PRG/STAFF.BIN"]
    assert len(orig) == len(new)
    allowed = set()
    for t in staff.TABLES:
        allowed.update(range(t, staff.read_table(orig, t)[1]))
    for off in staff.STREAMS:
        allowed.update(range(off, staff.stream_tim(orig, off)[2]))
    n = len(staff.read_layout(orig))
    allowed.update(staff.LAYOUT + i * 6 + b for i in range(n) for b in (2, 3))  # x only
    stray = [i for i in range(len(orig)) if orig[i] != new[i] and i not in allowed]
    assert not stray, [hex(i) for i in stray[:10]]
    assert [(ln, dy) for ln, _x, dy in staff.read_layout(new)] == [(ln, dy) for ln, _x, dy in staff.read_layout(orig)]


@needs_tree
def test_staff_lines_all_draw_on_screen_and_keep_clear_of_each_other(edited):
    new = edited["ESCA/PRG/STAFF.BIN"]
    credits, fnt = staff.load_credits(), font.Font()
    assert sorted(credits) == list(range(167))
    assert all(t.isascii() for t in credits.values())
    lines = sum(staff.read_all(new), [])
    assert [len(s) for s in lines] == [1 if credits[i] else 0 for i in range(167)]
    row, y = [], 0
    for line, x, dy in staff.read_layout(new) + [(0, 0, 999)]:
        if dy and row:  # a new row on screen: what shared the last one must not touch
            row.sort()
            assert all(a[1] + 4 <= b[0] for a, b in zip(row, row[1:])), row
            row = []
        if credits[line]:
            w = fnt.width(credits[line])
            assert lines[line][0][4] == w + staff.PAD and 0 <= x and x + w <= staff.SCREEN_X_MAX, (line, x, w)
            row.append((x, x + w))


@needs_tree
def test_staff_sprites_show_the_line_they_name(edited):
    """Each line's rectangle holds its own ink and nothing of its neighbours."""
    new = edited["ESCA/PRG/STAFF.BIN"]
    for s, lines in enumerate(staff.read_all(new)):
        dec, t, _end = staff.stream_tim(new, staff.STREAMS[s])
        px = np.frombuffer(dec, dtype=np.uint8, offset=t["pix"], count=t["end"] - t["pix"]).reshape(256, 128)
        full = np.zeros((256, 256), dtype=np.uint8)
        full[:, ::2], full[:, 1::2] = px & 15, px >> 4
        covered = np.zeros_like(full, dtype=bool)
        for segs in lines:
            for u, v, _x, _y, w, h in segs:
                covered[v:v + h, u:u + w + 1] = True  # + 1: a glyph's shadow may sit one past the advance
                assert full[v:v + h, u:u + w].any()
        assert not full[~covered].any(), f"sheet {s}: ink outside every sprite"


def tim_parts(data):
    t = timscan.parse(data, 0)
    return t, data[:t["pix"]], np.frombuffer(data, dtype=np.uint8, offset=t["pix"], count=t["end"] - t["pix"]).reshape(t["h"], t["w"] * 2)


@needs_tree
@pytest.mark.parametrize("name", ["ESCA111", "ZZZZZ2", "ZZZZZ3"])
def test_title_art_changes_only_inside_its_rects(edited, name):
    orig = (KUDO / f"{name}.TIM").read_bytes()
    new = edited[f"{gfx.KUDO}/{name}.TIM"]
    assert len(orig) == len(new)
    _t, head_o, a = tim_parts(orig)
    _t, head_n, b = tim_parts(new)
    assert head_o == head_n
    changed = a != b
    assert changed.any()
    x0, y0, x1, y1 = gfx.LOGO_RECT
    keep = np.ones_like(changed)
    if name == "ESCA111":
        keep[y0:y1, x0:x1] = False
    # the (c) glyph stays, and the BANDAI row and the menu words below and above it
    y = 161 if name == "ESCA111" else gfx.first_ink_row(a, 150)
    keep[y:y + 15, gfx.COPYRIGHT_TEXT_X:gfx.COPYRIGHT_END_X] = False
    assert not changed[keep].any(), name


@needs_tree
@pytest.mark.parametrize("n", sorted(gfx.CARDS))
def test_cards_keep_size_and_header_and_draw_in_their_own_palette(edited, n):
    orig = (KUDO / f"TI0{n}.TIM").read_bytes()
    new = edited[f"{gfx.KUDO}/TI0{n}.TIM"]
    assert len(orig) == len(new)
    t, _h, a = tim_parts(orig)
    t2, _h2, b = tim_parts(new)
    assert (t["w"], t["h"], t["x"], t["y"], t["cx"], t["cy"]) == (t2["w"], t2["h"], t2["x"], t2["y"], t2["cx"], t2["cy"])
    assert b.any() and set(np.unique(b)) <= set(np.unique(a))
    # one word in the accent colours, as the Japanese has one kanji (card 6's accent is a near-grey khaki)
    assert n == 6 or any(max(gfx.rgb(t["clut"][i])) - min(gfx.rgb(t["clut"][i])) >= 16 for i in np.unique(b))


def test_font_files_are_listed_with_a_licence():
    table = (ROOT / "docs/fonts.md").read_text(encoding="utf-8")
    for path in (gfx.SERIF, gfx.DISPLAY):
        assert path.is_file() and path.name in table
