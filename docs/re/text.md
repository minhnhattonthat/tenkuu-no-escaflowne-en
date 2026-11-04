# Text: encoding, codes, references

**Encoding: Shift-JIS, verified.** On-screen `「１３秒の壁を破れたら、私のファーストキス、お願いします。` equals SYO01 file 0x1A73C, and a breakpoint on the
glyph renderer logged the same codes in order (`tools/lua/drawlog.lua`, run `work/qa/draw`, state `work/qa/r1/s003600.sstate`).
Strings end in a NUL. Text is **not** compressed. Layout strings mix fullwidth glyphs used as opcodes; JIS X 0213/NEC symbols ①-⑳ and Ⅰ-Ⅹ are opcodes too.

## Opcodes (verified by reading the interpreter, 0x8003A3AC-0x8003AF1C, state at `w+0x34`)

`w` = window struct. A byte with bit 7 set starts a 2-byte code. **A byte below 0x80 is not text**: see "Digits".

| Bytes | Glyph | Effect |
|---|---|---|
| `00` | | End of string (state 1) |
| `0A`, `81AB` | `↓` | Newline (state 5) |
| `81A4` | `▽` | Wait for button (state 8; timer `w+0xD2` = 0x708 = 1800 frames) |
| `81A3` | `▲` | End page and close (state 0xA; timer 0x708) |
| `819D` | `◎` | Clear window / new page (state 0xF) |
| `81AA` | `↑` | Close (state 0xF, `w+0xD6`=0, `0x8009AE74`=-1, portrait off) |
| `81A0` | `□` | Menu wait: choice input (state 0x14) |
| `8173` / `8174` | `《` `》` | Name tag on/off (`w+0xCC` = -1 / 0) |
| `8740-8747` | `①-⑧` | Colour: `w+0xC6` = 1-8. Script uses ③ names, ② body, ④ choice numbers |
| `8748-874F` | `⑨-⑯` | Font flags in `w+0xC4`. `874B`, `874F` seen; `0x8000` = 12 px cell. Exact map still to be listed from 0x8003A588-0x8003A76C |
| `8785-8787` | | Also clear low nibble of `w+0xC4` (0x8003A65C-A6F8); not seen in script scan |
| `8754-875D` | `Ⅰ-Ⅹ` | Menu item markers, row positions stored at `w+0x4D8` |
| `8194` + 2 ASCII digits | `＃nn` | Sets `0x8009AE74` = nn (portrait/expression id; guess until seen) |
| `8197` + 4 ASCII digits | `＠nnnn` | Decimal id parsed at 0x8003A800 (1000s, 100s…). Guess: voice clip, since numbers rise line by line and the game is voiced. Keep these exactly. |
| `8196` | `＊` | State 0x1E; meaning unknown |
| `818F` + 2 bytes | `￥` | Literal: next 2 bytes draw as a glyph |

**Digits (0x8003AE14, code read):** bytes below 0x80 read as a 2-digit decimal pair and call `0x8001DABC(n-1)`, or `(-1)` for 26. Meaning of that call is a guess: portrait select, so `③26` = none and `③01` = portrait 0. Phase 5 must keep this working when ASCII text comes in. From the script scan, digit pairs appear only right after `③` inside `《…》`, so testing `w+0xCC` should separate them from text. Confirm over the whole script in phase 4 before relying on it.

Line limit (0x8003AC1C): `w+0x36` + advance (3 or 4 VRAM words) >= `w+0x30` forces a newline.

## Where strings live (`tools/text_recon.py`)

| Overlay | Strings | Text bytes | Reached by lui/addiu | Reached by word | No reference found |
|---|---|---|---|---|---|
| SYO00 | 86 | 1,614 | 38 | 45 | 3 |
| SYO01 | 394 | 27,455 | 312 | 45 | 37 |
| SYO02 | 450 | 30,640 | 359 | 45 | 46 |
| SYO03 | 541 | 40,674 | 483 | 45 | 13 |
| SYO04 | 584 | 41,675 | 527 | 45 | 12 |
| SYO05 | 338 | 24,093 | 288 | 45 | 5 |
| SYO06 | 368 | 23,768 | 311 | 45 | 12 |
| SYO07 | 445 | 32,958 | 368 | 45 | 32 |

Counts include some binary false positives (`ぎ…` runs inside code): the extractor must filter them.

- **Shared block, file 0x00C-0x8AE of every SYO:** partner menu, SAVE/LOAD, memory-card messages, character name table, some reached by 32-bit pointers (`by_word` 45). **8 copies, one per overlay, byte-identical (verified by sha1).** Translate once, write 8 times.
- **Scene-select menu:** after the shared block (e.g. SYO01 0x2758).
- **Inline battle barks:** e.g. SYO01 0x1B9C `◎《③26レフィーヌ》②↓「いくぞっ！▲`, embedded in records `00 00 00 0A 00 00 00 0B 00 00 80 11 … FF FF FF FF <string>`, reached by lui/addiu to the string start. These sit between records, so a longer string needs moving.
- **Main script block, after code:** SYO01 0x1A5F8-0x20A77, packed back to back with no alignment, NUL-separated. Most strings end `▲↓\0` or `▽↓\0`.

**References are MIPS `lui`/`addiu` pairs in overlay code (verified: SYO01 0x800C8E24 -> 0x800DC220, the first script string).** A string can have several (`multi_ref` 15-92 per overlay; e.g. 0x800DC251 from 0x800C8EB8 and 0x800DBED8). Every pair must be rewritten when text moves. One target in SYO01 lands mid-string.

**Strings with no reference (guess: dead dialogue).** SYO01's script block has 288 strings, 268 referenced, 20 not (e.g. 0x1B373 choice `じゃまだ、どけぇ！`). All 20 searched as 32-bit words in `MDAT01*`, BATTLE, MOVIE, EXE and `BADA1*`: no hit. For 4 of the 20, no `addiu`/`ori` in SYO01 carries the low half. Other overlays not checked this way. Extract and translate them anyway; they cost little and the proof is incomplete.

Text is in overlays only. MDAT, BATTLE, TITLE, MOVIE and STAFF hold no script (their SJIS scan hits are pixel noise).
