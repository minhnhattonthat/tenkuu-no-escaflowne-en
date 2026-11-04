"""cdcalls.py: list every CD command a program file issues, to prove loads go by name and no position is hardcoded.

  python -X utf8 tools/cdcalls.py   (reads work/tree: SLPS_010.15 and ESCA/PRG/*.BIN)

Finds calls to the three PsyQ entries below and reads the command from `addiu $a0,$zero,N` in the 6 words before the
call or its delay slot. CdlPlay needs a position set by CdlSetloc, so the call sites to read by hand are 2 and 3.
"""
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = {0x8005E048: "CdControl", 0x8005E180: "CdControlF", 0x8005E2AC: "CdControlB"}  # all three end in 0x8005F0CC
NAMES = {1: "Nop", 2: "Setloc", 3: "Play", 4: "Forward", 5: "Backward", 6: "ReadN", 7: "Standby", 8: "Stop", 9: "Pause",
         0xE: "Setmode", 0x13: "GetTN", 0x14: "GetTD", 0x15: "SeekL", 0x16: "SeekP", 0x1B: "ReadS"}


def calls(data):
    """Yield (word index, entry, command or None) for each call to an entry in ENTRIES."""
    words = struct.unpack("<%dI" % (len(data) // 4), data[:len(data) // 4 * 4])
    jals = {0x0C000000 | ((e & 0x0FFFFFFF) >> 2): e for e in ENTRIES}
    for i, w in enumerate(words):
        if w in jals:
            near = words[i + 1:i + 2] + words[max(i - 6, 0):i][::-1]
            imm = next((x & 0xFFFF for x in near if x >> 16 == 0x2404), None)
            yield i, jals[w], imm


if __name__ == "__main__":
    tree = ROOT / "work" / "tree"
    for p in [tree / "SLPS_010.15"] + sorted((tree / "ESCA" / "PRG").glob("*.BIN")):
        seen = list(calls(p.read_bytes()))
        print(p.name, dict(Counter(NAMES.get(c, c) for _, _, c in seen)))
        for i, _, c in seen:
            if c in (2, 3):
                print(f"  {NAMES[c]} at file 0x{i * 4:X}")
