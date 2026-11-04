"""text_recon.py: per overlay, which Shift-JIS runs a lui/addiu pair or raw pointer reaches, and the text-block layout.
Read-only recon; prints one summary line per overlay and the unreached runs. Run from anywhere."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mips
import sjis_scan

BASE = 0x800C1C28  # verified: SYO00/01 found at this address in RAM dumps (work/qa/r1)
TREE = ROOT / "work/tree/ESCA/PRG"


def nul_strings(d, runs):
    """Split runs into the NUL-terminated strings that hold them: (start, end)."""
    out = []
    for o, _t in runs:
        s = o
        while s > 0 and d[s - 1] != 0:
            s -= 1
        e = d.find(b"\0", o)
        if not out or out[-1] != (s, e):
            out.append((s, e))
    return out


def main():
    for f in sorted(TREE.glob("SYO*.BIN")):
        d = f.read_bytes()
        strs = nul_strings(d, list(sjis_scan.runs(d, 2)))
        code = {}
        for va, t, op in mips.lui_pairs(d, BASE):
            code.setdefault(t - BASE, []).append(va)
        words = {}
        for o in range(0, len(d) - 3, 4):
            v = struct.unpack_from("<I", d, o)[0]
            if BASE <= v < BASE + len(d):
                words.setdefault(v - BASE, []).append(o)
        hit_code = sum(1 for s, e in strs if s in code)
        hit_word = sum(1 for s, e in strs if s in words and s not in code)
        miss = [(s, e) for s, e in strs if s not in code and s not in words]
        tb = sum(e - s for s, e in strs)
        multi = sum(1 for s, e in strs if len(code.get(s, [])) > 1)
        tail = len(d) - len(d.rstrip(b"\0"))
        print(f"{f.name}: size {len(d)} strings {len(strs)} text_bytes {tb} lo {strs[0][0]:X} hi {strs[-1][1]:X} "
              f"by_code {hit_code} by_word {hit_word} none {len(miss)} multi_ref {multi} zero_tail {tail}")
        for s, e in miss[:40]:
            print(f"   none {s:06X}-{e:06X} {d[s:e].decode('cp932', 'replace')[:60]}")


if __name__ == "__main__":
    main()
