# Graphics-text survey

**Method.** Static sweep: `tools/gfx_sweep.py` found 15,207 TIMs (raw and LZ) on the disc, 986 unique by pixels, numbered in `work/survey/gfx/index.tsv` (rebuildable, gitignored). Every sheet was read; see "Who read what". FMV: `tools/fmv_sample.py`, 3 frames from each of 57 videos, no burned-in text seen.

Rendering uses each TIM's first CLUT. A label drawn in a different palette could read differently, not disappear.

## Needs English

| # | Screen | Source | Format | Japanese | Plan |
|---|---|---|---|---|---|
| 1 | Title logo | `TIM/KUDO/ESCA111.TIM` | raw, VRAM part of a 256 px sheet | `天空のエスカフローネ` logo | Official English logo exists ("The Vision of Escaflowne"), so redraw (D5). Other art in the sheet stays. |
| 2 | Title copyright | `ESCA111.TIM`, `ZZZZZ2.TIM`, `ZZZZZ3.TIM` | raw | `©サンライズ・テレビ東京` | `©SUNRISE / TV TOKYO`. Three copies (normal, red, white). |
| 3 | Chapter cards 1-7 | `TIM/KUDO/TI01-07.TIM` | raw, 61,984 B each | `第一章 異世界ガイア`, `第二章 幻の月`, `第三章 青き瞳の王子`, `第四章 失われた楽園`, `第五章 恋の黄金律作戦`, `第六章 黒き翼の天使`, `第七章 永遠の想い` | Redraw at same size, keep the coloured accent word. |
| 4 | Staff roll | `PRG/STAFF.BIN` LZ TIMs at 0x1D8C, 0x5490, 0x9404, 0xDA48 | LZ, 4bpp 256x256 each | All credits, about 60 rows of kanji | English credits (D3). Rows are probably sliced by code: read STAFF.BIN code for row layout. Names need romanization research. |
| 5 | Story-title sheet | `TIM/KUDO/ST_TITL.TIM` | raw, VRAM (832,256) | `第 章 一 二 三 四 五`; and `ゴメスを倒せ`, `五郎とゴロー`, `鳥を見た`, `カネゴンの繭`, `開けてくれ` | The five titles look like Ultra Q episode names (from memory, unchecked), so likely placeholder art. TITLE.BIN's card file table loads it for each chapter (0x801DF870), but all 7 `chN_card` proofs show only the TI0N title, never these five. Guess: loaded, not drawn. Settle it in phase 8: replace it with a marker and rewatch a card. |
| 6 | Placeholder | MDAT01A G00647 (and other MDATs as dups) | LZ | `作成中` ("under construction") | Check whether it shows. Replace if it can. |

## Already English or not language text (leave alone)

| Element | Source | Note |
|---|---|---|
| Title menu | `ZZZZZ2/3`, `ESCA111` | `START LOAD OPTION` |
| Bandai logo | `STR/00/BANDAI.STR` | |
| Game over | SYO00 file 0x4D2C (and copies in every SYO) | `GAME OVER` |
| Battle HUD | `BATI11` G00011 (other BATIs not separately read if dup) | Script-font English names (`Escaflowne, Enemy, Scherazade, …, Guymelef`), `PAUSE`, A-Z, 0-9 |
| Battle digits | `BADA11` G00000 | `012345` |
| Tarot cards | `TA_00-07`, `TALOT2`, MDAT tarot TIMs | Italian names (`IL FUOCO/LA LUCE`, `LA GIUSTIZIA`…) are original design. Leave them. |
| Window frames | EXE TIMs 0x2F8B4-0x381D4 | No text |

| Shrine offertory box | MDAT01A G01013 (0x8F370), Earth shrine scene | `奉` painted on the box, about 16 px. Set dressing on a real Japanese shrine, like a sign in a photo. Default: leave it (non-blocking question in `docs/status.md`). |
| Stone wall runes | MDAT04D G07238 (0x6FC20) | Zoomed: rows of invented squiggles, not a language. Leave. |

## Who read what

- Read by the implementer: KUDO, STAFF, EXE and SYO images, battle sheet 0, all 194 unique non-sprite MDAT images, gfx sheets 15, 31, 32.
- Independent read-only pass: `codex exec` over gfx sheets 1-30 except 15 (`work/survey/codex_sprites.txt`). Its only new text hits were the two rows above, each then checked by zooming; the rest were tarot titles, already listed. Its tarot spellings are its own reading of tiny text, not checked.
- Skipped by the sweep, on purpose: `SOUND/*`, `*.STR` (sampled separately), `TITLE_B.DAT` (tilemap guess), `license_data.dat`, `TRACK-02.WAV`. Non-TIM pixel data, if any exists, is invisible to it: the runtime tour is the backstop.

## Drawn by the text engine (text work, not graphics)

Partner menu, SAVE/LOAD, memory-card messages, YES/NO, LOAD/EXIT window on title (seen in `work/qa/t_opt`). Names are in the script.

## Confirmed at runtime (phase 2, `tools/debug/warp_all.py`, proofs in `work/qa/warp/_proof/`)

- Title: draws `START` and `LOAD` only, plus the Japanese copyright row. **There is no OPTION screen:** the cursor word only takes 0 and 1 (`docs/re/warp.md`), so the OPTION label in the art is never drawn and needs no redraw.
- Chapter cards 1-7, `GAME OVER`, staff roll and battle HUD all draw as listed above. SAVE/LOAD, partner menu and choice boxes use the text engine.
- Not seen in any run: `作成中` (row 6).

The rule stays: a row counts as done only with a zoomed cold-boot shot in phase 8.

**FMV dialogue:** FMVs have spoken Japanese and no on-screen text, so nothing burned in needs replacing. Subtitling them is optional engine work; see `docs/status.md`.
