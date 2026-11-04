"""syo_map.py: read-only map of each chapter overlay's main routine (scene switch, overlay calls).

  syo_map.py [N ...]    prints, per chapter: entry, scene-select menu, jump table, and the ordered calls in main.

Overlay indexes for 0x80014E40(n), read from the EXE name table: 0 MOVIE, 1 BATTLE, 2 TITLE, 3 STAFF.
"""
import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs

BASE = 0x800C1C28
PRG = Path("work/tree/ESCA/PRG")
SYO00_DISPATCH = (0x800C4984, 0x18)  # first load in SYO00's switch, one per chapter


def entries():
    """Read each chapter's entry from SYO00's dispatcher: lui a1 / addiu a1 before jal 0x80037904."""
    d = (PRG / "SYO00.BIN").read_bytes()
    out = {}
    for ch in range(1, 8):
        o = SYO00_DISPATCH[0] - BASE + (ch - 1) * SYO00_DISPATCH[1]
        hi = struct.unpack_from("<I", d, o + 8)[0] & 0xFFFF
        lo = struct.unpack_from("<h", d, o + 12)[0]
        out[ch] = (hi << 16) + lo & 0xFFFFFFFF
    return out


def walk(d, entry):
    """Yield (va, name, a0) for each jal from entry to the function's jr ra, with a0 tracked by constant load."""
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    regs = {}
    pending = None
    for i in md.disasm(d[entry - BASE:entry - BASE + 0x8000], entry):
        w = struct.unpack("<I", i.bytes)[0]
        op = w >> 26
        rs, rt = (w >> 21) & 31, (w >> 16) & 31
        imm = struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]
        if op == 0x0F:
            regs[rt] = (w & 0xFFFF) << 16
        elif op == 0x09:
            regs[rt] = (regs.get(rs, 0) if rs else 0) + imm & 0xFFFFFFFF
        elif op == 0x0D:
            regs[rt] = regs.get(rs, 0) | (w & 0xFFFF)
        elif op == 0 and (w & 0x3F) == 0x21:  # move
            rd = (w >> 11) & 31
            regs[rd] = regs.get(rs, 0) if rs else regs.get(rt, 0) if rt else 0
        if pending is not None:
            yield i.address - 4, pending, regs.get(4)
            pending = None
        if op == 3:
            pending = (i.address & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
        if w == 0x03E00008:
            break


def table(d, entry):
    """Find `lui at,hi; addu at,at,v0; lw v0,lo(at); jr v0` in main; return (table_va, count)."""
    words = struct.unpack("<%dI" % 0x200, d[entry - BASE:entry - BASE + 0x800])
    sext = lambda x: struct.unpack("<h", struct.pack("<H", x & 0xFFFF))[0]
    for k, w in enumerate(words):
        if w == 0x00400008 and words[k - 2] >> 26 == 0x23:  # jr v0 after lw v0,lo(at)
            lui = next(words[j] for j in range(k - 3, k - 8, -1) if words[j] >> 26 == 0x0F)
            n = next(words[j] & 0xFFFF for j in range(k - 3, k - 12, -1) if words[j] >> 26 == 0x0B)  # sltiu
            add = next(sext(words[j]) for j in range(k - 3, k - 12, -1) if words[j] >> 16 == 0x2443)  # addiu v1,v0,imm
            return ((lui & 0xFFFF) << 16) + sext(words[k - 2]) & 0xFFFFFFFF, n, add
    return None


def calls(d, want):
    """Yield (jal_va, a0) for every jal target in `want` across the overlay, a0 from the nearest load in the 4 words before or the delay slot."""
    sext = lambda x: struct.unpack("<h", struct.pack("<H", x & 0xFFFF))[0]
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    for k in range(4, n - 1):
        w = words[k]
        if w >> 26 != 3 or 0x80000000 | ((w & 0x03FFFFFF) << 2) not in want:
            continue
        a0 = None
        for j in (k + 1, k - 1, k - 2, k - 3, k - 4):
            x = words[j]
            if x >> 26 == 0x09 and (x >> 16) & 31 == 4 and (x >> 21) & 31 == 0:
                a0 = sext(x)
                break
            if x == 0x00002021:  # move a0,zero
                a0 = 0
                break
        yield BASE + k * 4, 0x80000000 | ((w & 0x03FFFFFF) << 2), a0


def main():
    es = entries()
    want = [int(a) for a in sys.argv[1:]] or sorted(es)
    for ch in want:
        d = (PRG / f"SYO{ch:02d}.BIN").read_bytes()
        e = es[ch]
        print(f"== chapter {ch} SYO{ch:02d} entry {e:08X}")
        t = table(d, e)
        if t:
            va, n, add = t
            print(f"  table {va:08X} n={n} index=scene+{add}")
            seen = {}
            for k in range(n):
                tgt = struct.unpack_from("<I", d, va - BASE + 4 * k)[0]
                seen.setdefault(tgt, []).append(k - add)
            for tgt, scenes in sorted(seen.items()):
                print(f"    {tgt:08X}: scenes {scenes}")
        for va, tgt, a0 in walk(d, e):
            a = "?" if a0 is None else hex(a0)
            print(f"  {va:08X} jal {tgt:08X} a0={a}")
        print("  -- overlay loads anywhere in the file")
        for va, tgt, a0 in calls(d, {0x80014E40}):
            if a0 != 0:
                print(f"  {va:08X} jal {tgt:08X} overlay={a0}")


if __name__ == "__main__":
    main()
