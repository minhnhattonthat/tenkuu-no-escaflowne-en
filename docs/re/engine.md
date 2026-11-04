# Text engine and font

**One renderer, verified:** `0x80039AD4(sjis, flags*, dest)` is called once, from the interpreter at 0x8003ADA8. Breakpoint log: `work/qa/draw/log.txt` (`tools/lua/drawlog.lua`, needs `--debugger`).

**Font: BIOS kanji ROM** via `Krom2RawAdd` (B0:51, stub at 0x8007B018), 16x15 1bpp. Three other callers sit in 0x80067B28-BB8 (SDK kanji helper; no callers in EXE, SYO01 or BATTLE disassembly; guess: dead).

**Horizontal squeeze:** 0x80039C14-C44 folds each 16-pixel row to 12 by OR-ing neighbouring columns (`c000 | 3c00<<1 | 3c0<<2 | 3c<<3 | 3<<4`). `w+0xC4` bit 0x8000 selects the 12 px cell (3 VRAM words at 4bpp) against 16 px (4 words). Bits 0x40, 0x1, 0x2 OR a row with itself shifted; no string sets them, and the rewritten renderer drops them.

**Upload:** each glyph goes through `0x80063A7C(RECT*, pixels)` (LoadImage) at `(w+0x2C + w+0x36, w+0x2E + w+0x38)`, from a per-window buffer `w+0xD8 + 0x200*i`, `i` cycling 0-1, with `0x800637B8(0)` (DrawSync) when it wraps. Buffers must survive until the transfer ends.

**States after a glyph (verified by reading 0x8003AF1C-0x8003B0E4 and the unit test running it):** 3 goes straight to 4. State 4: unless `w+0xCC` is negative, count it up to `w+0xCE` over frames (typing speed), then add the cell's words to `w+0x36`; at `w+0x30` or more go to state 5 (newline), else state 2 (read the next byte). State 2 loops within one call, so several glyphs can share a frame.

**Measured (first dialogue of chapter 1, `work/qa/draw`):** window at texture x=388; rows y=281 (name), 297, 313: 16-pixel line step. Unit is the VRAM word = 4 screen pixels, so the stock engine can't place a glyph finer than 4 px.

## The hook (`asm/vwf.asm`; verified: `tests/test_vwf.py`, full warp `work/qa/marker`)

Proportional ASCII, and two-letter codes so English stays near the Japanese byte count.

- **Entry:** a byte below 0x80 reaches 0x8003AE14. Inside a name tag an ASCII digit is still the portrait id; anything else is a character. Bytes 01-1F (not 0A) and A0-DF are pairs from `tbl/dte.txt`; no string uses them (`tools/extract.py`).
- **Pen:** in pixels at `w+0x4C0`. `w+0x36` stays the pen in words, rounded up, so newline, wrap and menu marks work untouched. A colour change moves to the next word, or carried pixels would change colour too.
- **Compose:** per-row carry at `w+0x4C8` holds the pixels already drawn in the word the pen is inside. These fields live in the tail of glyph buffer 1, which a glyph never reaches (at most 96 of 512 bytes).
- **Wrap:** a glyph or pair past `w+0x30` x 4 px sets state 5 and rereads the byte.
- **After a glyph:** like the original, state 3 and buffers 0-1 with DrawSync at the wrap. `w+0x36` is left short by the cell's words because state 4 adds them. Skipping this drew whole lines in one frame and ran the buffer index past the window array: floor tiles came up striped black.
- **Pair of characters:** both drawn in one step, so English types 1-2 characters per tick against 1 Japanese glyph.
- **The renderer** (0x80039AD4) is rewritten smaller, pixel-equal to the original (unit test), and the font sits in the room that frees.

Font and script format: `fonts/vwf.txt` (`tools/font.py`), `{` can't appear in English text (it opens a token). Insertion: `tools/insert.py`; a fullwidth indent stays Shift-JIS and keeps its 12 px.

**Stale-state risk:** `w+0x40` holds a RAM pointer into the overlay; savestates break across text rebuilds.

## Width gate (`tools/debug/width_gate.py`, `work/qa/gate`; numbers in `data/windows.json`)

- Text draws over the portraits. The line limit is the window's 224 px, and 223 px of `W` shows every column.
- The wait arrow covers x 267-276 across both body rows, so body rows stop at 208 px.
- A page holds 3 rows: name plus 2, or 3 with no name. A 4th row shows its top half under the frame.
- A line past the limit wraps by itself and pushes the rest down, so lines should break by hand.
- About 5.25 px per character in running text: 39 characters per body row, 78 per named page. Japanese max: 16 per row.
- Glyph torture (printable ASCII except `{`, double spaces): read clean in `work/qa/gate/ch1_sm10`.
- Not reached: partner prompts (see `data/windows.json`). The marker fill itself is byte-limited (160-224 px per overlay), so a marker line ending early in a box isn't a clip.
