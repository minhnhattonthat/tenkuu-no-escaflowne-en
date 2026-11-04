"""The text hook, run under unicorn on the assembled EXE: the Shift-JIS renderer is pixel-equal to the routine it
replaced, and the VWF path composes glyphs across VRAM words, wraps and decodes pairs. Unicorn doesn't model the R3000
load delay; the emulator runs (docs/re/engine.md) cover that."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dte  # noqa: E402
import extract  # noqa: E402
import font  # noqa: E402
import insert  # noqa: E402

uc = pytest.importorskip("unicorn")
from unicorn import UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS32  # noqa: E402
from unicorn.mips_const import UC_MIPS_REG_29, UC_MIPS_REG_30, UC_MIPS_REG_31, UC_MIPS_REG_4, UC_MIPS_REG_5, UC_MIPS_REG_6  # noqa: E402

LOAD_IMAGE, RESUME, DIGITS, DRAW_SYNC, STATES_DONE = 0x80063A7C, 0x8003AF1C, 0x8003AE1C, 0x800637B8, 0x8003B0E4
KROM, RENDER, VWF_LOW, TWO_BYTE, VWF_HIGH_SITE = 0x8007B018, 0x80039AD4, 0x8003AE14, 0x8003A44C, 0x8003A444
STOP = 0x80000F00
WIN, FP, FAKE_GLYPH = 0x80100000, 0x801F0000, 0x80110000
PHYS = 0x1FFFFFFF


@pytest.fixture(scope="module")
def exe(tmp_path_factory):
    if not (extract.TREE / insert.EXE).is_file() or not insert.ARMIPS.is_file():
        pytest.skip("no tree or armips")
    out = tmp_path_factory.mktemp("en")
    insert.assemble(out, dte.Dte())
    return (out / insert.EXE).read_bytes()


class Ram:
    """Unicorn runs KSEG0 from physical 0 but its mem_read and mem_write take physical addresses: mask them."""

    def __init__(self):
        self.uc = uc.Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        self.uc.mem_map(0, 0x200000)

    def __getattr__(self, name):
        return getattr(self.uc, name)

    def mem_write(self, addr, data):
        self.uc.mem_write(addr & PHYS, data)

    def mem_read(self, addr, size):
        return self.uc.mem_read(addr & PHYS, size)


def machine(image):
    """RAM with the EXE at its load address."""
    m = Ram()
    m.mem_write(0x80010000, image[0x800:])
    m.reg_write(UC_MIPS_REG_29, FP - 0x1000)
    return m


def stub(m, addr, words):
    m.mem_write(addr, struct.pack(f"<{len(words)}I", *words))


JR_RA_NOP = [0x03E00008, 0]


def render(image, code_ptr, flags):
    """Call the renderer with a font pointer from the stub; return the 128 buffer bytes."""
    m = machine(image)
    hi, lo = (code_ptr >> 16) & 0xFFFF, code_ptr & 0xFFFF
    stub(m, KROM, [0x3C020000 | hi, 0x03E00008, 0x34420000 | lo])  # lui v0 / jr ra / ori v0
    m.mem_write(FAKE_GLYPH, bytes(range(1, 31)))
    m.mem_write(WIN, struct.pack("<4H", flags, 2, 15, 1))
    m.reg_write(UC_MIPS_REG_4, 0x889F)
    m.reg_write(UC_MIPS_REG_5, WIN)
    m.reg_write(UC_MIPS_REG_6, WIN + 0x100)
    m.reg_write(UC_MIPS_REG_31, STOP)
    m.emu_start(RENDER, STOP, count=200000)
    assert m.reg_read(uc.mips_const.UC_MIPS_REG_2) == WIN + 0x100
    return bytes(m.mem_read(WIN + 0x100, 128))


@pytest.mark.parametrize("flags, size", [(0x8080, 96), (0x8000, 96), (0x0080, 128)])
def test_sjis_renderer_matches_the_original(exe, flags, size):
    orig = (extract.TREE / insert.EXE).read_bytes()
    assert render(exe, FAKE_GLYPH, flags)[:size] == render(orig, FAKE_GLYPH, flags)[:size]


def test_sjis_renderer_on_unknown_code_matches_the_original(exe):
    orig = (extract.TREE / insert.EXE).read_bytes()
    assert render(exe, 0xFFFFFFFF, 0x8080)[:96] == render(orig, 0xFFFFFFFF, 0x8080)[:96]


class Run:
    """The interpreter's state on reaching a byte below 0x80: window fields and the locals the hook reads."""

    def __init__(self, image, text=b"", pen_x=0, limit=56, name_tag=False):
        self.m = machine(image)
        m = self.m
        self.uploads, self.buffers, self.syncs = [], [], 0
        stub(m, LOAD_IMAGE, JR_RA_NOP)
        # a real call clobbers the temporaries: t0, t1, t3, t5 = 0
        stub(m, DRAW_SYNC, [0x00004021, 0x00004821, 0x00005821, 0x00006821] + JR_RA_NOP)
        m.hook_add(uc.UC_HOOK_CODE, self._on_sync, begin=DRAW_SYNC, end=DRAW_SYNC)
        m.mem_write(WIN + 0x34, struct.pack("<h", 2))
        m.mem_write(WIN + 0x30, struct.pack("<h", limit))
        m.mem_write(WIN + 0x2C, struct.pack("<2H", 388, 281))
        m.mem_write(WIN + 0x36, struct.pack("<h", pen_x))
        m.mem_write(WIN + 0xC4, struct.pack("<4H", 0x8080, 2, 15, 1))
        m.mem_write(WIN + 0xCC, struct.pack("<h", -1 if name_tag else 0))
        m.mem_write(WIN + 0x40, struct.pack("<I", WIN + 0x1000))
        m.mem_write(WIN + 0x1000, text)
        m.mem_write(FP + 0x60, struct.pack("<I", WIN))
        m.reg_write(UC_MIPS_REG_30, FP)
        m.hook_add(uc.UC_HOOK_CODE, self._on_load_image, begin=LOAD_IMAGE, end=LOAD_IMAGE)

    def _on_load_image(self, _m, addr, size, _):
        m = self.m
        rect = struct.unpack("<4h", m.mem_read(m.reg_read(UC_MIPS_REG_4), 8))
        self.buffers.append(m.reg_read(UC_MIPS_REG_5))
        self.uploads.append((rect, bytes(m.mem_read(m.reg_read(UC_MIPS_REG_5), rect[2] * 2 * rect[3]))))

    def _on_sync(self, *_):
        self.syncs += 1

    def byte(self, b, start=VWF_LOW, new_call=True):
        """Run the hook on one byte, then the original code for the states it leaves; return where it left to."""
        m = self.m
        m.mem_write(FP + 0x2E, struct.pack("<H", b))
        if new_call:
            m.mem_write(FP + 0x1E, struct.pack("<H", 0))
        ends = []
        h = m.hook_add(uc.UC_HOOK_CODE, lambda mm, a, s, _: (ends.append(a), mm.emu_stop()), begin=RESUME, end=RESUME)
        h2 = m.hook_add(uc.UC_HOOK_CODE, lambda mm, a, s, _: (ends.append(a), mm.emu_stop()), begin=DIGITS, end=DIGITS)
        h3 = m.hook_add(uc.UC_HOOK_CODE, lambda mm, a, s, _: (ends.append(a), mm.emu_stop()), begin=TWO_BYTE, end=TWO_BYTE)
        m.emu_start(start, 0, count=400000)
        for x in (h, h2, h3):
            m.hook_del(x)
        if ends[0] == RESUME:
            m.emu_start(RESUME, STATES_DONE, count=1000)
        return ends[0]

    def field(self, off, fmt="<h"):
        return struct.unpack(fmt, self.m.mem_read(WIN + off, struct.calcsize(fmt)))[0]

    def screen(self, width=224):
        """Paint every upload onto a window-sized canvas; rows of pixels as colour values."""
        canvas = [[15] * width for _ in range(16)]
        for (x, _y, w, h), data in self.uploads:
            for r in range(h):
                for i in range(w * 2):
                    b = data[r * w * 2 + i]
                    px = (x - 388) * 4 + i * 2
                    if px < width:
                        canvas[r][px] = b & 15
                    if px + 1 < width:
                        canvas[r][px + 1] = b >> 4
        return canvas


def expected(text, fnt, width=224):
    """What the text should look like: ink where the font has a bit, shadow right under ink, background elsewhere."""
    ink = [[0] * width for _ in range(16)]
    pen = 0
    for ch in text:
        w, rows = fnt.glyphs[ch]
        for r, bits in enumerate(rows):
            for x in range(w):
                if bits & (0x80 >> x):
                    ink[r + 2][pen + x] = 1
        pen += w + 1
    out = [[15] * width for _ in range(16)]
    for r in range(16):
        for x in range(width):
            if ink[r][x]:
                out[r][x] = 2
            elif r and ink[r - 1][x]:
                out[r][x] = 1
    return out, pen


TEXT = "Hello, Hitomi! Wmil..."


def test_glyphs_compose_across_words(exe):
    run = Run(exe)
    for ch in TEXT:
        assert run.byte(ord(ch)) == RESUME
    want, pen = expected(TEXT, font.Font())
    assert run.screen() == want
    assert run.field(0x4C0, "<H") == pen
    assert run.field(0x36) == (pen + 3) // 4
    assert run.field(0x34) == 2


def test_pair_code_draws_two_characters(exe):
    dt = dte.Dte()
    run = Run(exe)
    low = dt.code["he"]  # a code from the table; which range it falls in decides the entry point
    high = next(c for c in dt.text if c >= 0xA0)
    assert low < 0x20
    assert run.byte(low) == RESUME
    assert run.byte(high, start=VWF_HIGH_SITE) == RESUME
    want, _pen = expected("he" + dt.text[high], font.Font())
    assert run.screen() == want
    assert len(run.uploads) == 4


def test_a_glyph_takes_the_original_pacing_state(exe):
    run = Run(exe)
    hook_ends = []
    run.m.hook_add(uc.UC_HOOK_CODE, lambda m, a, s, _: hook_ends.append(run.field(0x34)), begin=RESUME, end=RESUME)
    run.byte(ord("H"))
    assert hook_ends[0] == 3


def test_glyphs_in_one_call_stay_in_two_buffers(exe):
    # 48 uploads in one frame ran the original's index past the windows: floor tiles went black
    run = Run(exe)
    for i, ch in enumerate(TEXT):
        assert run.byte(ord(ch), new_call=i == 0) == RESUME
    want, _pen = expected(TEXT, font.Font())
    assert run.screen() == want
    assert set(run.buffers) == {WIN + 0xD8, WIN + 0x2D8}
    assert run.syncs == (len(TEXT) - 1) // 2


def test_two_byte_codes_still_reach_the_original_path(exe):
    run = Run(exe)
    assert run.byte(0x81, start=VWF_HIGH_SITE) == TWO_BYTE
    assert run.byte(0xE0, start=VWF_HIGH_SITE) == TWO_BYTE


def test_digit_in_name_tag_is_the_portrait_id(exe):
    run = Run(exe, name_tag=True)
    assert run.byte(ord("2")) == DIGITS
    assert not run.uploads
    assert run.byte(ord("V")) == RESUME
    assert len(run.uploads) == 1


def test_digit_in_body_is_a_glyph(exe):
    run = Run(exe)
    assert run.byte(ord("2")) == RESUME
    assert len(run.uploads) == 1


def test_wrap_rereads_the_byte(exe):
    run = Run(exe, limit=3)  # 12 pixels: one "W" (7 px + gap) fits, the next doesn't
    assert run.byte(ord("W")) == RESUME
    assert run.field(0x34) == 2
    before = run.field(0x40, "<I")
    assert run.byte(ord("W")) == RESUME
    assert run.field(0x34) == 5
    assert run.field(0x40, "<I") == before - 1
    assert len(run.uploads) == 1


def test_pair_that_would_overflow_wraps_whole(exe):
    dt = dte.Dte()
    run = Run(exe, limit=3)
    assert run.byte(ord("W")) == RESUME
    before = run.field(0x40, "<I")
    assert run.byte(dt.code["he"]) == RESUME
    assert (run.field(0x34), run.field(0x40, "<I"), run.field(0x4C4, "<B")) == (5, before - 1, 0)


def test_filling_the_line_exactly_starts_a_new_one(exe):
    run = Run(exe, limit=2)  # "H" 7 advance + "i" 2 advance = 9, 8 px shown: the trailing gap doesn't count
    assert font.Font().width("Hi") == 8
    assert run.byte(ord("H")) == RESUME
    assert run.byte(ord("i")) == RESUME
    assert run.field(0x34) == 5


def test_colour_change_starts_a_new_word(exe):
    run = Run(exe)
    assert run.byte(ord("i")) == RESUME          # 1 px + gap: pen 2
    run.m.mem_write(WIN + 0xC6, struct.pack("<H", 3))
    assert run.byte(ord("i")) == RESUME
    assert run.uploads[1][0][0] == 389           # next word, not the one holding the first "i"
    assert run.field(0x4C0, "<H") == 6


def test_encode_packs_english_after_a_fullwidth_indent():
    dt = dte.Dte()
    jp = insert.jptext.Jp()
    assert insert.encode("　[c7]he{nl}", jp, dt) == b"\x81\x40[c7]" + bytes([dt.code["he"]]) + jp.encode("{nl}")


def test_font_fits_the_hook():
    fnt = font.Font()
    blob = fnt.blob()
    assert len(blob) == 95 + 95 * 12
    assert max(w for w, _ in fnt.glyphs.values()) <= 8  # 3 px carry + 9 advance = 3 words, one glyph buffer row
