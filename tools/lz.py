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


def compress(data):
    """A stream the game's 0x800157CC reads: 0xFA (0xF0 ^ 10 distance bits), a 24-bit token count, then flags and tokens.
    decompress() starts after those 4 bytes. Greedy, which is all a mostly blank sheet needs."""
    max_len, max_dist = 66, 1024
    last, tokens, i = {}, [], 0
    while i < len(data):
        best, dist = 0, 0
        for p in reversed(last.get(data[i:i + 3], [])[-64:]):
            if i - p > max_dist:
                break
            n = 0
            while n < max_len and i + n < len(data) and data[p + n] == data[i + n]:
                n += 1
            if n > best:
                best, dist = n, i - p
        if best >= 3:
            tokens.append((True, (best - 3) << 10 | (dist - 1)))
        else:
            best = 1
            tokens.append((False, data[i]))
        for k in range(i, i + best):
            last.setdefault(data[k:k + 3], []).append(k)
        i += best
    out = bytearray(b"\xFA" + len(tokens).to_bytes(3, "little"))
    for g in range(0, len(tokens), 8):
        group = tokens[g:g + 8]
        out.append(sum(0x80 >> n for n, (ref, _v) in enumerate(group) if ref))
        for ref, v in group:
            out += v.to_bytes(2, "little") if ref else bytes([v])
    return bytes(out)
