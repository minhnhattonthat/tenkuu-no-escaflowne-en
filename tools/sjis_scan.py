"""sjis_scan.py FILE.. [--min N] [--show N]: list Shift-JIS runs holding kana per file (recon helper; read-only)."""
import argparse
from pathlib import Path


def runs(d, minlen=4):
    """Yield (offset, text) for maximal double-byte/ASCII runs with at least one kana."""
    i, n = 0, len(d)
    while i < n:
        s, out = i, []
        while i < n:
            b = d[i]
            if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEA) and i + 1 < n and (0x40 <= d[i + 1] <= 0xFC and d[i + 1] != 0x7F):
                try:
                    out.append(d[i:i + 2].decode("cp932"))
                except UnicodeDecodeError:
                    break
                i += 2
            elif 0x20 <= b < 0x7F and out:
                out.append(chr(b))
                i += 1
            else:
                break
        t = "".join(out)
        if len(t) >= minlen and any("぀" <= c <= "ヿ" for c in t):
            yield s, t
        if i == s:
            i += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min", type=int, default=4)
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    for f in a.files:
        d = Path(f).read_bytes()
        r = list(runs(d, a.min))
        print(f"{f}: {len(d)} bytes, {len(r)} runs, {sum(len(t) for _, t in r)} chars")
        for o, t in r[:a.show]:
            print(f"  {o:06X} {t}")
