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
| `8748-874F` | `⑨-⑯` | Font flags in `w+0xC4`; `0x8000` = 12 px cell. **No string uses them** (the earlier `874B`, `874F` sightings were code noise; extraction proves it), so the exact map doesn't matter unless phase 5 wants them |
| `8785-8787` | | Also clear low nibble of `w+0xC4` (0x8003A65C-A6F8); no string uses them |
| `8754-875D` | `Ⅰ-Ⅹ` | Menu item markers, row positions stored at `w+0x4D8` |
| `8194` + 2 ASCII digits | `＃nn` | Sets `0x8009AE74` = nn (portrait/expression id; guess until seen) |
| `8197` + 4 ASCII digits | `＠nnnn` | Decimal id parsed at 0x8003A800 (1000s, 100s…). Guess: voice clip, since numbers rise line by line and the game is voiced. Keep these exactly. |
| `8196` | `＊` | State 0x1E (set at 0x8003A7EC); meaning unknown. Used in 126 debug labels in SYO00 (`Ｍ１Ｂ１＊＊▲`) and one dialogue line, SYO01 0x1CFF8 (`名は、ひとみ…。＊＊↓と言う訳です。`); guess: a timed pause. Keep it |
| `818F` + 2 bytes | `￥` | Literal: next 2 bytes draw as a glyph. No string uses it |

**Digits (0x8003AE14, code read):** bytes below 0x80 read as a 2-digit decimal pair and call `0x8001DABC(n-1)`, or `(-1)` for 26. Meaning of that call is a guess: portrait select, so `③26` = none and `③01` = portrait 0. Phase 5 must keep this working when ASCII text comes in. **Verified over every string (`test_digits_are_only_the_id_in_a_name_tag`):** all ASCII in the script is one 2-digit pair right after the colour code inside `《…》`, so testing `w+0xCC` separates them from text. `＃` always has 2 ASCII digits and `＠` 4 (`test_token_arguments_are_decimal`).

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

**References are MIPS `lui`/`addiu` pairs in overlay code (verified: SYO01 0x800C8E24 -> 0x800DC220, the first script string).** A string can have several (`multi_ref` 15-92 per overlay; e.g. 0x800DC251 from 0x800C8EB8 and 0x800DBED8). Every pair must be rewritten when text moves. Every reference instruction is an `addiu`; none reads text with `lw` or `lb`.

Each entry in `script/*.json` lists its own references (`site`, `va`). What the extractor had to sort out (`tools/extract.py`, `tests/test_extract.py`):
- **False references (4):** `addiu $a1` before `jal 0x80037904` (the loader) is the next overlay's entry point, which lands in this overlay's script by chance: SYO02 0x800D4598, SYO03 0x800D92F4, SYO05 0x800D0AD4, SYO06 0x800D2C88. Rewriting them would break the chapter change. Dropped.
- **Mid-string references (2, both real):** SYO02 0x17C90 and SYO03 0x1C3BB begin with retired lines `欠番↓` ("number retired") and code points past them. Each is split into a `dead` + `no_end` head and a live tail.
- **`numbers` block in SYO01 (99 refs into record bytes):** 20-byte records (`idx`, `02B0`, `FFFFFFFF`, string). The refs read the records, so they stay put.
- **Word references:** only the 49-name table (SYO00 file 0x50CC; every overlay has its own copy of the table), all 4-aligned.

**Strings with no reference: dead (verified as far as a static read goes).** 61 entries carry `dead` (`test_dead_means_nothing_points_at_it`): 5 in the shared block (`パートナーを終了`, `Ｓ Ａ Ｖ Ｅ`, `Ｌ Ｏ Ａ Ｄ` rows, `とのパートナー行動を終了しますか？`, its yes/no), and 56 in the chapters, 2 of them the `欠番` heads. No `addiu`, `ori` or load in their overlay carries the low half of any of their addresses. A word search of the program files and every ESCA `.BIN`/`.DAT` for any entry's start address finds only 0x800C2080 (18 MDATs, twice each, at a structural spot; a live menu string in an overlay, and MDAT holds no code) and 0x800E05FF (MDAT04B/D/F); guess: chance. Translate them anyway: cheap, and a static read can't rule out a computed address.

**Fragments (`form: fragment`):** the partner prompts are built at runtime as name + piece: `X` + `をパートナーにしますか？`, `X` + `から、` + `Y` + `に、↓パートナーを交代しますか？`. The name comes first, so English has to word around that order, or phase 5 has to change the join.

**Text outside the overlays:**
- `BATTLE.BIN` 0x1B8 `文字列` ("string") goes to window 0 at 0x801EF3E4; 0x1D8 `↑` closes it. Whether it ever shows is unchecked; the marker build will tell. Its 6 bytes hold a short English word in place.
- EXE 0x6FC84 `天空のエスカフローネ`: the memory-card title the BIOS draws. Shift-JIS only: stays fullwidth in English, field 64 bytes (`SC 13 01` is at 0x6FC80).
- `MDAT`, `TITLE`, `MOVIE`, `STAFF`: nothing else. `extract.py --check` proves it two ways: a raw scan (3+ characters, with kana or fullwidth) and every `lui`/`addiu` or word target outside the ranges that decodes as Japanese (1+ character). Noise found that way is listed as `data` in `tbl/text_ranges.tsv`.
- No code builds glyph codes as immediates in the overlays, BATTLE, TITLE, MOVIE or STAFF (`ori rX,$zero,0x81xx-0x98xx`: 0 hits); the EXE's 25 hits are the interpreter's own opcode compares (0x8003A47C on). Phase 5's marker build is the runtime check.
