"""lz.py: the game's LZ codec. A control byte gives 8 flags, MSB first: 0 = literal byte, 1 = 16-bit LE ref.
Ref: len = (v >> 10) + 3, dist = (v & 0x3FF) + 1. Hand-derived from a compressed TIM header; see docs/re/compression.md."""


def decompress(d, off=0, limit=None, size=None):
    """Return (output, end_offset). Stops at `size` output bytes or `limit` input bytes."""
    out = bytearray()
    i = off
    n = len(d) if limit is None else min(len(d), off + limit)
    while i < n and (size is None or len(out) < size):
        fl = d[i]
        i += 1
        for b in range(7, -1, -1):
            if i >= n or (size is not None and len(out) >= size):
                break  # shortcut: a real stream's unused trailing flags aren't validated, only size is
            if fl >> b & 1:
                if i + 2 > n:
                    return bytes(out), i
                v = d[i] | d[i + 1] << 8
                i += 2
                dist = (v & 0x3FF) + 1
                if dist > len(out):
                    raise ValueError(f"bad ref at {i - 2:X}: dist {dist} > {len(out)}")
                for _ in range((v >> 10) + 3):
                    out.append(out[-dist])
            else:
                out.append(d[i])
                i += 1
    return bytes(out), i
