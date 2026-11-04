"""dte.py: two-letter codes for English text (asm/vwf.asm draws them).

tbl/dte.txt holds 94 pairs, one per line, written between | so a space shows. `python -X utf8 tools/dte.py --build`
recomputes them from the `en` text in script/ and rewrites the file; run it once the translation changes much.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
TABLE = ROOT / "tbl/dte.txt"
CODES = [c for c in range(1, 0x20) if c != 0x0A] + list(range(0xA0, 0xE0))
SLOTS = 0x20 + 0x40
TOKEN = re.compile(r"(\{[^}]*\})")


def load(path=TABLE):
    pairs = [ln[1:3] for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    if len(pairs) != len(CODES) or len(set(pairs)) != len(pairs):
        raise ValueError(f"{path}: need {len(CODES)} different pairs, found {len(pairs)}")
    bad = [p for p in pairs if any(not " " <= c <= "~" or c.isdigit() for c in p)]
    if bad:
        raise ValueError(f"{path}: pairs must be printable ASCII without digits (portrait ids): {bad}")
    return pairs


class Dte:
    def __init__(self, path=TABLE):
        self.pairs = load(path)
        self.code = {p: c for p, c in zip(self.pairs, CODES)}
        self.text = {c: p for p, c in self.code.items()}

    def blob(self):
        """2 bytes per slot: codes 00-1F, then A0-DF, as asm/vwf.asm indexes them."""
        out = bytearray(SLOTS * 2)
        for c, p in self.text.items():
            slot = c if c < 0x20 else c - 0xA0 + 0x20
            out[slot * 2:slot * 2 + 2] = p.encode("ascii")
        return bytes(out)

    def pack(self, run):
        """ASCII text -> bytes, greedily. Digits stay single, so portrait ids in a name tag can't be touched."""
        out, i = bytearray(), 0
        while i < len(run):
            c = self.code.get(run[i:i + 2])
            if c is not None:
                out.append(c)
                i += 2
            else:
                out.append(ord(run[i]))
                i += 1
        return bytes(out)

    def unpack(self, data):
        """Bytes of one ASCII run -> text; the inverse of pack, for tests."""
        return "".join(self.text.get(b, chr(b)) for b in data)


def build():
    pairs = Counter()
    for p in (ROOT / "script").glob("*.json"):
        for e in json.loads(p.read_text(encoding="utf-8"))["entries"]:
            for part in TOKEN.split(e.get("en", "")):
                if part and not part.startswith("{"):
                    pairs.update(part[i:i + 2] for i in range(len(part) - 1))
    usable = [(n, k) for k, n in pairs.items() if all(" " <= c <= "~" and not c.isdigit() for c in k)]
    best = [k for _n, k in sorted(usable, key=lambda x: (-x[0], x[1]))][:len(CODES)]
    if len(best) < len(CODES):
        sys.exit(f"only {len(best)} pairs in the script: nothing to rebuild from yet")
    TABLE.write_text("# Two-letter codes, written by tools/dte.py --build. Between | so a space shows.\n"
                     + "".join(f"|{k}|\n" for k in best), encoding="utf-8", newline="\n")
    print(f"{TABLE}: {len(best)} pairs")


if __name__ == "__main__":
    if sys.argv[1:] == ["--build"]:
        build()
    else:
        print(__doc__)
