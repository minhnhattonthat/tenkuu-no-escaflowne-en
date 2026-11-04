# Disc layout

**Dump:** SLPS-01015, `rom.sha1`. Track 1 MODE2/2352 (515,612,496 bytes), track 2 CD audio. `SYSTEM.CNF` boots
`SLPS_010.15`. Unpack: `python -X utf8 tools/unpack.py` -> `work/tree`, `work/layout.xml`.

**Prior work (2026-11-04 search):** no English patch found. A Tumblr project (Hoodiemonkey, 2014) subtitled one video and
stopped; no patch or tools released. A cdromance sidebar "New English Patched" line is unverified and looks unrelated.

| Path | Size | Contents |
|---|---|---|
| `SLPS_010.15` | 571,392 | Main EXE. Load 0x80010000, size 0x8B000, entry 0x8005CE50, SP 0x801FFFF0. Text engine lives here. Only SJIS: `天空のエスカフローネ` at file 0x6FC84 (memory-card title, preceded by `SC 13 01`). |
| `ESCA/PRG/SYO00-07.BIN` | 21 K-159 K (SYO07 546 K) | Chapter overlays: code + all dialogue. SYO07's last 266,243 bytes are zero. |
| `ESCA/PRG/BATTLE,MOVIE,TITLE,STAFF.BIN` | 34-130 K | Battle, FMV player, title, staff-roll overlays. No script text. STAFF holds 4 LZ TIMs of credits. |
| `ESCA/BG/00,01/MDATnnX.BIN` | up to 829 K | Per-scene adventure data: pointer table + ~400-500 LZ TIMs each (portraits, sprites, map art). `MDATnnJ` (30,076 B) is a stub with 2 TIMs. |
| `ESCA/BATTLE/ACTn/BADAnn,BATInn.BIN` | up to 327 K | Battle data and images. 20-byte files are empty stubs. Named sub-entries (timestamp + name + offsets). |
| `ESCA/TIM/KUDO/*` | 16-66 K | Raw TIMs: title, chapter cards `TI01-07`, tarot `TA_00-07`, `TALOT2`, `ST_TITL`, `ZZZZZ2/3`; `TITLE_B.DAT` = 16-part tilemap (guess: title background, no text seen). |
| `ESCA/STR/00-02/*.STR` | 57 files | MDEC FMV 320x240, 18,627 frames (~21 min) with XA audio. |
| `ESCA/SOUND/` | `BGM`, `SE`, `STR01-07` | Audio; STR01-07 hold voice clips (`＠nnnn` in script). Guess: index by chapter. |

**Load addresses (verified: `tools/ramfind.py` on RAM dumps `work/qa/r1/ram_003600.bin`):**
- `SYOnn.BIN` at **0x800C1C28** (59 of 64 samples of SYO01 match there).
- `MDAT01A.BIN` at **0x801060A4** (58 of 64 samples). Holds absolute pointers, so it is not relocatable as-is.
- `TITLE.BIN`, `BATTLE.BIN`, `MOVIE.BIN` at **0x801D8000** (TITLE/MOVIE from RAM; BATTLE from jal-target scoring, 50 prologue hits: guess until seen in RAM).
- Overlay loader: `0x80037A7C`, name table at 0x80010F94 (0x60 bytes per name).

**Identity build plan (phase 3):** `dumpsxiso` + `mkpsxiso` with `work/layout.xml`. mkpsxiso rebuilds license from
`license_data.dat`; the dump's EDC/ECC and subheaders are what the test will compare, by sha1 of track 1.

**Scene select left in overlays (for phase 2):** each `SYOnn` holds a menu `◎Ⅷ第１章　Ⅹ戻る↓Ⅰシーン１　Ⅱシーン９…`
(SYO01 file 0x2758, SYO02 0x1580, SYO07 0x1244). Not yet known how to reach it; find the caller of that string first.
