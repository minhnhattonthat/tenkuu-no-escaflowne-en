# Text engine and font

**One renderer, verified:** `0x80039AD4(sjis, flags*, dest)` is called once, from the interpreter at 0x8003ADA8. Breakpoint log: `work/qa/draw/log.txt` (`tools/lua/drawlog.lua`, needs `--debugger`).

**Font: BIOS kanji ROM** via `Krom2RawAdd` (B0:51, stub at 0x8007B018), 16x15 1bpp. Three other callers sit in 0x80067B28-BB8 (SDK kanji helper; no callers in EXE, SYO01 or BATTLE disassembly; guess: dead).

**Horizontal squeeze:** 0x80039C14-C44 folds each 16-pixel row to 12 by OR-ing neighbouring columns (`c000 | 3c00<<1 | 3c0<<2 | 3c<<3 | 3<<4`). `w+0xC4` bit 0x8000 selects the 12 px cell (3 VRAM words at 4bpp) against 16 px (4 words). Bits 0x40, 0x1, 0x2 OR a row with itself shifted (guess: bold, top-half and bottom-half bold).

**Upload:** each glyph goes through `0x80063A7C(RECT*, pixels)` (guess: `LoadImage`; verified the RECTs are sane VRAM positions). Rect is 3x16 or 4x16 VRAM words at `(w+0x2C + w+0x36, w+0x2E + w+0x38)`, from a per-window buffer `w+0xD8 + 0x200*i`, `i` cycling 0-1, with `0x800637B8(0)` (guess: `DrawSync`) when it wraps. If so, buffers must survive until the transfer ends.

**Measured box (verified, `work/qa/draw`, first dialogue of chapter 1):**
- Texture page origin x=388, rows y=281 (name), 297, 313 (body): 16-pixel line step.
- Body text 16 glyphs x 3 words per line (x 388-433), so 12 px glyphs across 192+ px. Real width limit `w+0x30` still to be read.
- Unit is the VRAM word = 4 screen pixels, so the stock engine cannot place a glyph at finer than 4 px.

**Typing:** one glyph per frame in the log (frame 145, 146…), with some glyphs sharing a frame. Timer 0x708 auto-advances after 1800 frames.

## Proposal for phase 5 (not yet tested)

English needs a **proportional font with pixel placement**. 12 px cells give ~16 characters per line, far too few.

1. **Hook 0x8003AE14** (the below-0x80 branch): if `w+0xCC` is set (inside `《》`) and the byte is a digit, run the original portrait parse; otherwise treat it as ASCII text.
2. **VWF renderer:** keep a per-window 4bpp line buffer in RAM, OR the next glyph in at the pen's pixel x, and `LoadImage` only the words it touched. Pixel pen lives beside `w+0x36`; the newline and clear states reset it. Start from the 4bpp ink values the 16x15 path writes, so colour codes still work.
3. **Font data:** drawn 1bpp glyphs + width table in the hook block (`free-space.md`). Roughly 96 glyphs x 30 bytes.
4. **Menus:** rows stored at `w+0x4D8` and the choice cursor may assume glyph cells; check in the marker build.
5. Byte budget: SJIS costs 2 bytes per glyph and ASCII 1, so ~2x the characters fit in the same bytes. Reference rewriting is still needed since string lengths change.

Fallback if the VWF hook fails: fixed 8 px half-width cell (2 words), about 24 characters per line, no pixel compositing.

**Stale-state risk:** `w+0x40` holds a RAM pointer into the overlay; savestates break across text rebuilds.
