"""ramfind.py RAM.bin FILE..: where each disc file's 64-byte samples sit in a 2 MB PS1 RAM dump (finds overlay load addresses)."""
import sys
from pathlib import Path

ram = Path(sys.argv[1]).read_bytes()
for f in sys.argv[2:]:
    d = Path(f).read_bytes()
    hits = {}
    step = max(len(d) // 64, 64)
    for o in range(0, max(len(d) - 64, 1), step):
        s = d[o:o + 64]
        if len(set(s)) < 8:
            continue
        p = ram.find(s)
        if p >= 0:
            b = 0x80000000 + p - o
            hits[b] = hits.get(b, 0) + 1
    print(f, {hex(k): v for k, v in sorted(hits.items(), key=lambda x: -x[1])[:3]})
