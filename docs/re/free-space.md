# Free space

**Candidates unless marked trap-tested.** Zero at one moment proves nothing: 0x800A01A8-A21A8 and others are BSS the game may fill later. Measured on `work/qa/r1/ram_003600.bin` and `ram_005400.bin` (chapter 1, first scene). Before use: fill with a trap value, tour, and search code for references.

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

**These zero runs are live images, trap-tested (`tools/lua/trap.lua`, `work/qa/trap`):** 0x80082090 is wiped at boot, and 0x80083750-952 is read by libgpu at 0x8006542C and 0x80065498. Don't use them.

**In use by the hook (trap-tested, `work/qa/trap2`: 9 scenes covering dialogue, menus, battle, save, load, credits; only the BIOS loader and the hook itself touch them):**

| VA | Bytes | Holds |
|---|---|---|
| 0x80010254-0x800104AC | 600 | hook parts 1 and 3 |
| 0x80011C28-0x80011F50 | 808 | hook part 2, pair table; was libgpu's debug format strings, read only by its dump calls at debug level > 0 |
| 0x80039AD4-0x8003A1A8 | 1,748 | smaller renderer, then the font (1,235 bytes) |

**Other low RAM:** 0x8000BED2-0x8000E000 (8,494) and 0x8000E5A0-0x80010000 (6,752) below the EXE are zero at runtime, but the BIOS and libraries may use them. Not loadable from the EXE image without extending the load range. Avoid.

**After EXE end:** 0x8009B000 onward is BSS up to the overlay. 0x800B1148-0x800BE514 (54,220) shrinks to 48,032 after play, so it is in use.

## Disc

`mkpsxiso` lays files out from `layout.xml`, so a grown file moves the rest. The game finds files by name through `CdSearchFile`, so LBAs are not hardcoded and files may grow (verified, `disc.md`). Disc capacity is no constraint at 515 MB.
