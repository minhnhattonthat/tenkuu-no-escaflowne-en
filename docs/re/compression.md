# Compression

**Codec: `tools/lz.py` (decoder only).** Control byte gives 8 flags, MSB first: 0 = literal byte, 1 = 16-bit little-endian ref with `len = (v >> 10) + 3`, `dist = (v & 0x3FF) + 1`. So a 1 KB window and copies of 3-66 bytes.

**Verified:** derived by hand from a TIM header, then `tools/timscan.py scan_lz` decoded 15,207 TIMs across the disc whose declared sizes come out exact (`work/survey/count.txt`). Decompressor routine: 0x800157CC, header and encoder in `docs/re/graphics.md`. Output size comes from the TIM header; no end marker seen. An encoder that reproduces the game's bytes is not needed unless the identity test goes through recompression: edited TIMs only need any valid stream plus a block that fits.

**Container, battle files (partly guessed):** `BATInn.BIN` = timestamp (u32), name (16 bytes, e.g. `bati11.bin`), then u32 offsets, then entries, each timestamp + name + offsets (e.g. `eft_un_t.bin`). Block data begins with a u32 of unknown meaning (`FA 72 0E 00`; `0xFA` low byte repeats, guess: checksum or tag), then the LZ stream.

**MDAT:** u32 id (`0F 00 00 00`), then absolute RAM pointers based at 0x801060A4 (verified base by RAM dump). LZ TIMs follow. Compressed length isn't stored beside each TIM as far as seen.

**STAFF.BIN:** 4 LZ TIMs at file 0x1D8C, 0x5490, 0x9404, 0xDA48, between code and data. Find their references before changing size: the file is code-loaded and addresses may be hardcoded. Fit replacements in the same bytes if possible (text-only images compress well).
