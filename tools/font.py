"""font.py: compile fonts/vwf.txt for the hook, and measure text with it.

    font.Font().blob()          95 advance bytes, then 12 row bytes per glyph (MSB = left), for 0x20-0x7E
    font.Font().width("text")   pixels the text takes on screen (the last glyph's gap doesn't count)

    python -X utf8 tools/font.py --sheet out.png    render every glyph, shadow included, to check by eye
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = 12
FULLWIDTH_PX = 12


def load(path=None):
    """{char: (width, [row bytes])}. Raises on a malformed or missing glyph."""
    glyphs = {}
    for ln in Path(path or ROOT / "fonts/vwf.txt").read_text(encoding="utf-8").splitlines():
        if not ln or ln.startswith("##"):
            continue
        ch, top, *rows = ln.split(" ")
        ch = " " if ch == "SP" else ch
        w, top = len(rows[0]), int(top)
        if len(ch) != 1 or ch in glyphs or not 1 <= w <= 8 or any(len(r) != w for r in rows) or top + len(rows) > ROWS:
            raise ValueError(f"bad glyph line: {ln!r}")
        out = [0] * ROWS
        for i, r in enumerate(rows):
            out[top + i] = int(r.replace(".", "0").replace("#", "1").ljust(8, "0"), 2)
        glyphs[ch] = (w, out)
    missing = [chr(c) for c in range(0x20, 0x7F) if chr(c) not in glyphs]
    if missing:
        raise ValueError(f"font misses {missing}")
    return glyphs


class Font:
    def __init__(self, path=None):
        self.glyphs = load(path)

    def blob(self):
        order = [self.glyphs[chr(c)] for c in range(0x20, 0x7F)]
        return bytes(w + 1 for w, _ in order) + b"".join(bytes(rows) for _, rows in order)

    def width(self, text):
        """A fullwidth space is one 12 px Shift-JIS cell, which has no 1 px gap to drop at the end."""
        px = sum(FULLWIDTH_PX if c == "　" else self.glyphs[c][0] + 1 for c in text)
        return px - (1 if text and text[-1] != "　" else 0)


def sheet(path):
    from PIL import Image
    font = Font()
    lines = ["".join(chr(c) for c in range(0x20 + i, min(0x20 + i + 32, 0x7F))) for i in range(0, 95, 32)]
    lines += ["The quick brown fox jumps over the lazy dog.", "Hitomi: \"Van-sama! Is that... an Escaflowne?\""]
    img = Image.new("RGB", (240, 16 * len(lines)), (40, 50, 40))
    for y, line in enumerate(lines):
        pen = 0
        for ch in line:
            w, rows = font.glyphs[ch]
            for r, bits in enumerate(rows):
                for x in range(w):
                    if bits & (0x80 >> x):
                        img.putpixel((pen + x, y * 16 + r + 2), (240, 240, 240))
                        if not (r < 11 and rows[r + 1] & (0x80 >> x)):
                            img.putpixel((pen + x, y * 16 + r + 3), (0, 0, 0))
            pen += w + 1
    img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(path)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--sheet":
        sheet(sys.argv[2])
    else:
        print(__doc__)
