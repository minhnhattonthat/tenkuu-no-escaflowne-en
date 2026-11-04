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

**Identity build (verified: `tests/test_identity.py`, also fails when one tree byte is flipped):** `tools/build.py`
runs `mkpsxiso` on `work/layout.xml` from `work/`. The output is one .bin holding both tracks; its first 515,612,496
bytes hash to the track 1 pin and the rest to the track 2 pin, so EDC/ECC, subheaders, license and the trailing dummies
all rebuild exactly. `work/tree` must stay the pristine unpack: English goes in a copy, or the test fails.

**Files are found by name (verified):**
- Static: every file the game loads is named `\ESCA\...;1` in the EXE or an overlay. `tools/cdcalls.py` lists every
  CD command: 13 Setloc sites, none with a literal position. EXE sites read a `CdSearchFile` (0x8005FCE0) result, a
  stored file struct, or libcd's own path; the MOVIE.BIN site (0x801D9128) takes a pointer argument from its caller
  at 0x801D8BD0, not traced further. Voice and sound offsets are added to the stored file position (`CdPosToInt` 0x8005E578, `CdIntToPos`
  0x8005E474), so they are relative to the file.
- Dynamic: `tools/build.py --shift 1000` puts 1000 empty sectors ahead of every file, moving the EXE, every overlay
  and track 2. `warp_all.py --cue` on it: 145/145 ok, cold boot through save, load, battles, FMVs, credits.
  - Frames at a fixed frame number do differ, because seek time moves everything. Of 145 proof frames, 41 differ by
    over 2%, all reviewed by eye: same scene, later or earlier animation. A control rerun on the original disc
    reproduced the earlier frames, so the runs are deterministic per layout and the change comes from the layout.
  - `ch1_s12` run to frame 9000 on both discs: same path (battle, FMV, dialogue, same map screen). The battle itself
    plays differently, since timing changes mash and AI.
  - **So any file growth changes frame timing:** don't judge a later build by same-frame pixel diffs against the
    original.
  - Not proven by this run: voice clips and music play correctly (the check is pictures only). Their positions are
    file-relative by the static read above.
- **Track 2 is never played:** no CdlPlay, GetTN or GetTD in any program file (`test_no_cd_audio_commands`), so track 1
  may grow without moving anything the game relies on.

**Scene select left in overlays (for phase 2):** each `SYOnn` holds a menu `◎Ⅷ第１章　Ⅹ戻る↓Ⅰシーン１　Ⅱシーン９…`
(SYO01 file 0x2758, SYO02 0x1580, SYO07 0x1244). Not yet known how to reach it; find the caller of that string first.
