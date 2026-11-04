# Free space

**All of these are candidates, none trap-tested.** Zero at one moment proves nothing: 0x800A01A8-A21A8 and others are BSS the game may fill later. Measured on `work/qa/r1/ram_003600.bin` and `ram_005400.bin` (chapter 1, first scene). Before use: fill with a trap value, tour, and search code for references.

## Inside a SYO overlay

SYO loads at 0x800C1C28 and MDAT at 0x801060A4, so at most **279,676 bytes** (0x4447C) are available for overlay + its BSS.

Zero runs after SYO01's end (0x800E31B0) at runtime:

| Range | Bytes |
|---|---|
| 0x800E315C-0x800E88A4 | 22,344 |
| 0x800E8EC0-0x800ED0A4 | 16,868 |
| 0x801032D4-0x801060A4 | 11,728 |

Non-zero data between them shows the gap is used, by something not yet identified. Find it before growing any overlay.

**SYO07 confirms the limit (verified from the file):** real content ends at 0x26C7C. Then zeros, then a single byte `0E` at file 0x4447C = VA 0x801060A4, exactly the MDAT base, in the place where MDAT files keep their id (`0F`, `10`…, `31`). Then zeros to 545,920. So SYO07 was linked with a data section at the MDAT slot, and overlay + BSS must end by 0x801060A4. Largest real overlay content is SYO07 at 0x26C7C (158,844 bytes), with SYO04 at 0x26C0C.

Not yet known: does the SYO07 load overwrite the MDAT slot, and in what order the two load. Chapter 7 is the case to test.

**English size:** JP text is 2 bytes per glyph. English is 1 byte per character at about 2x the characters, so expect roughly neutral size per overlay. Plan to repack each script block in place and rewrite every lui/addiu pair. Tail growth is only a fallback.

## Inside the EXE (for hook code + font)

EXE loads 0x80010000-0x8009B000. Internal zero runs (file offset):

| File | VA | Bytes |
|---|---|---|
| 0x0399EA | 0x800491EA | 4,138 |
| 0x072820 | 0x80082020 | 4,208 (RAM dump shows 0x80082090-80082DD0 still zero) |
| 0x071D4C | 0x8008154C | 1,044 |

0x800491EA-0x8004A214 is still zero at runtime in the middle of code and is the first choice for the hook (~1-2 KB). 0x80082090 is the first choice for font data (~3 KB).

**Other low RAM:** 0x8000BED2-0x8000E000 (8,494) and 0x8000E5A0-0x80010000 (6,752) below the EXE are zero at runtime, but the BIOS and libraries may use them. Not loadable from the EXE image without extending the load range. Avoid.

**After EXE end:** 0x8009B000 onward is BSS up to the overlay. 0x800B1148-0x800BE514 (54,220) shrinks to 48,032 after play, so it is in use.

## Disc

`mkpsxiso` lays files out from `layout.xml`, so a grown file moves the rest. The EXE and overlay names are looked up by name through the ISO9660 directory (`\ESCA\PRG\SYO01.BIN;1`; guess: `CdSearchFile`, see strings `searching...`, `dir..`), so LBAs are not hardcoded. Verify in phase 3. Disc capacity is no constraint at 515 MB.
