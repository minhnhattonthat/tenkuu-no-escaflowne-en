"""jptext.py: the Japanese text codec for this game (Shift-JIS + the engine's layout opcodes).

    import jptext
    jp = jptext.Jp()
    text, size = jp.decode(rom, 0x1A5F8)      # text ends with {end}, size includes the NUL
    assert jp.encode(text) == rom[0x1A5F8:0x1A5F8 + size]

Why not only tbl.Table: the payload is cp932, several thousand characters, and a .tbl line
per character would be unreadable. `tbl/jp.tbl` holds the opcodes; every other 2-byte
sequence decodes as its cp932 character when cp932 re-encodes it to the same bytes. When it
would not (Shift-JIS has duplicate mappings, e.g. 0x8790 and 0x81E0 both decode to ≒), the
bytes decode as `[XX][YY]` and encode back unchanged, so decode -> encode is always exact.

Bytes below 0x80 are ASCII (the engine reads ASCII digit pairs as an id argument, e.g. the
`26` in `《③26レフィーヌ》`), except 00 (end) and 0A (newline), which the table names.
Anything else below 0x20 is unknown and stays `[XX]`.

    python -X utf8 tools/jptext.py SYO01.BIN 1A5F8 [N]   decode N strings from an offset
    python -X utf8 tools/jptext.py --tokens FILE         count every token in all text
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from tbl import Table  # noqa: E402

LEAD = range(0x81, 0xA0)  # cp932 lead bytes, part 1
LEAD2 = range(0xE0, 0xFD)  # cp932 lead bytes, part 2
TERM = "end"


class Jp:
    def __init__(self, tbl_path=None):
        self.t = Table.load(tbl_path or ROOT / "tbl/jp.tbl")
        self.codes = sorted(self.t.ctrl, key=len, reverse=True)
        self.chars = {ch: code for ch, code in self.t.enc.items()}

    def _lead(self, b):
        return b in LEAD or b in LEAD2

    def _char_at(self, data, pos):
        """(2-byte cp932 char, bytes) at pos if it survives re-encoding, else None."""
        b = data[pos]
        if not self._lead(b) or pos + 1 >= len(data):
            return None
        pair = bytes(data[pos:pos + 2])
        if not (0x40 <= pair[1] <= 0xFC) or pair[1] == 0x7F:
            return None
        try:
            ch = pair.decode("cp932")
        except UnicodeDecodeError:
            return None
        return (ch, pair) if ch.encode("cp932") == pair else None

    def decode(self, data, pos=0, maxlen=65536):
        """Decode one string from pos. Returns (text, size); text ends with {end}."""
        start, out = pos, []
        while True:
            if pos >= len(data):
                raise ValueError(f"ran off the end at {pos:#x} decoding from {start:#x}")
            if pos - start >= maxlen:
                raise ValueError(f"no end within {maxlen} bytes at {start:#x}")
            for code in self.codes:
                if data[pos:pos + len(code)] == code:
                    name, argc = self.t.ctrl[code]
                    args = bytes(data[pos + len(code):pos + len(code) + argc])
                    if len(args) != argc:
                        raise ValueError(f"{name} at {pos:#x} is cut short")
                    pos += len(code) + argc
                    out.append(f"{{{name}:{args.hex().upper()}}}" if argc else f"{{{name}}}")
                    if name == TERM:
                        return "".join(out), pos - start
                    break
            else:
                pair = self._char_at(data, pos)
                if pair:
                    out.append(pair[0])
                    pos += 2
                elif 0x20 <= data[pos] < 0x7F:
                    out.append(chr(data[pos]))
                    pos += 1
                elif self._lead(data[pos]) and pos + 1 < len(data) and data[pos + 1] >= 0x40:
                    # a 2-byte code cp932 won't re-encode: keep the pair so the next glyph stays in step
                    out.append(f"[{data[pos]:02X}][{data[pos + 1]:02X}]")
                    pos += 2
                else:
                    out.append(f"[{data[pos]:02X}]")
                    pos += 1

    def encode(self, text):
        """Encode text (tokens, cp932 characters and ASCII) back to bytes."""
        out, i = bytearray(), 0
        while i < len(text):
            if text[i] == "{":
                j = text.find("}", i)
                if j < 0:
                    raise ValueError(f"unclosed token at {i} in {text!r}")
                name, _, args = text[i + 1:j].partition(":")
                if name not in self.t.ctrl_enc:
                    raise ValueError(f"unknown token {{{name}}} at {i} in {text!r}")
                code, argc = self.t.ctrl_enc[name]
                raw = bytes.fromhex(args)
                if len(raw) != argc:
                    raise ValueError(f"{{{name}}} needs {argc} arg bytes at {i} in {text!r}")
                out += code + raw
                i = j + 1
            elif text[i] == "[" and i + 3 < len(text) and text[i + 3] == "]":
                out.append(int(text[i + 1:i + 3], 16))
                i += 4
            else:
                ch = text[i]
                if ch in self.chars:
                    out += self.chars[ch]
                elif ord(ch) < 0x80:
                    out.append(ord(ch))
                else:
                    try:
                        out += ch.encode("cp932")
                    except UnicodeEncodeError as e:
                        raise ValueError(f"not encodable at {i}: {ch!r} in {text!r}") from e
                i += 1
        return bytes(out)

    def tokens(self, text):
        """Control-token names in text, in order (for lint and batch checks)."""
        names, i = [], 0
        while i < len(text):
            if text[i] == "{":
                j = text.find("}", i)
                names.append(text[i + 1:j].partition(":")[0])
                i = j + 1
            else:
                i += 1
        return names


def main():
    a = sys.argv[1:]
    jp = Jp()
    if not a:
        print("usage: jptext.py FILE OFF [N] | --tokens FILE")
        return
    if a[0] == "--tokens":
        d = Path(a[1]).read_bytes()
        counts = {}
        pos = 0
        while pos < len(d):
            try:
                text, size = jp.decode(d, pos)
            except ValueError:
                pos += 1
                continue
            for name in jp.tokens(text):
                counts[name] = counts.get(name, 0) + 1
            pos += size
        for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"{n:6d} {{{name}}}")
        return
    d = Path(a[0]).read_bytes()
    pos, n = int(a[1], 16), int(a[2]) if len(a) > 2 else 1
    for _ in range(n):
        text, size = jp.decode(d, pos)
        print(f"{pos:06X} {size:4d} {text}")
        pos += size


if __name__ == "__main__":
    main()
