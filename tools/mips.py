"""mips.py: MIPS recon helpers (capstone). Read-only. Addresses are hex without 0x.

  mips.py dis FILE LOADADDR START END          disassemble VAs (EXE: LOADADDR 8000F800, file offset 0x800 = 80010000)
  mips.py xref FILE LOADADDR TARGET [RANGE]    lui/addiu(ori,lw,sw..) pairs and raw .word pointers reaching TARGET..TARGET+RANGE
  mips.py hex FILE OFF LEN                     hex + cp932 dump
"""
import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs


def md():
    m = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    m.skipdata = True  # overlays mix code and text: keep going past undecodable words
    return m


def dis(d, base, start, end):
    for i in md().disasm(d[start - base:end - base], start):
        print(f"{i.address:08X} {i.bytes[::-1].hex()} {i.mnemonic} {i.op_str}")


def lui_pairs(d, base):
    """Yield (va_of_low_insn, target, kind) for lui rX,hi followed within 16 insns by an I-type using rX."""
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    for i, w in enumerate(words):
        if w >> 26 != 0x0F:
            continue
        rt = (w >> 16) & 31
        hi = w & 0xFFFF
        for j in range(i + 1, min(i + 17, n)):
            x = words[j]
            op, rs, rt2 = x >> 26, (x >> 21) & 31, (x >> 16) & 31
            imm = x & 0xFFFF
            if rs == rt and op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                low = imm if op == 0x0D else (imm - 0x10000 if imm & 0x8000 else imm)
                yield base + j * 4, (hi << 16) + low & 0xFFFFFFFF, op
            if (op == 0x0F and rt2 == rt) or (op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25) and rt2 == rt):
                break


def xref(d, base, target, rng=1):
    for va, t, op in lui_pairs(d, base):
        if target <= t < target + rng:
            print(f"code {va:08X} -> {t:08X} op={op:02X}")
    for o in range(0, len(d) - 3, 4):
        v = struct.unpack_from("<I", d, o)[0]
        if target <= v < target + rng:
            print(f"word {base + o:08X} (file {o:06X}) -> {v:08X}")


def hexd(d, off, ln):
    for o in range(off, off + ln, 16):
        row = d[o:o + 16]
        print(f"{o:06X} {row.hex(' '):<48} {row.decode('cp932', 'replace').translate({i: '.' for i in range(32)})}")


if __name__ == "__main__":
    cmd, f, *a = sys.argv[1:]
    d = Path(f).read_bytes()
    n = [int(x, 16) for x in a]
    {"dis": lambda: dis(d, *n), "xref": lambda: xref(d, *n), "hex": lambda: hexd(d, *n)}[cmd]()
