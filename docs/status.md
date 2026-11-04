# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 4. Extract, not started (phase 3 done).
- **Done:**
  - Step 0: dump pinned, tools fetched (`AGENTS.md` lists versions and URLs), hook and check active, guard proven, original boots to title on real BIOS.
  - Phase 1: `docs/re/` holds encoding, opcodes, references, text ranges, engine, free-space candidates, LZ codec, graphics survey. Start at `docs/re/README.md`.
  - Phase 2: `tools/debug/warp_all.py` reaches 145 scenes from cold boot by RAM poke, on the original disc: title, LOAD, SAVE, memory-card save and load back into the saved chapter, partner menu, choice box, all 7 chapter cards and scene menus, every scene-table entry, all 43 battle sites (types 0-3), game over (direct and by losing), winning a battle, credits, 3 endings. How it works: `docs/re/warp.md`. Proof sheets read by the implementer and independently by `codex exec`; that read caught a false pass on `choice_box` and thin proofs for save and load, all fixed.
  - Phase 3: `tools/build.py` rebuilds a byte-identical disc; `tests/test_identity.py` proves it on each check and fails when one tree byte is flipped. Build boots (`--smoke`). Files are found by name and track 2 is never played, so files may grow: `tools/build.py --shift 1000` passed the full warp, 145/145 (`docs/re/disc.md`).
- **Next (phase 4):** extract the script to `script/` (JSON) with `tools/tbl.py`: `encode(decode())` roundtrip test on every string, coverage test on the text ranges in `docs/re/text.md`, non-text marked. Start from `tools/text_recon.py`.
- **Open bugs:** none.
- **Not verified:**
  - Keyboard input in the PCSX-Redux GUI (Step 0 asks for it): this run is headless, nobody pressed a key. Scripted input and Lua are proven.
  - `choice_box` pokes a real choice string into a window to prove the box draws. The game's own route to it (partner trigger, then yes/no) wasn't run, nor was picking a choice. Phase 8's story-order run covers it.
  - `battle_ch7_57` and `battle_ch7_58` show identical frames; the call sites pass different stages. Guess: shared stage data.
  - Eight tiles show a generic prompt, GAME OVER or a dark frame, so the picture can't tell which checkpoint it is (`ch1_sm5`, `ch1_sm7`, `ch2_sm3`, `ch3_sm4`, `ch5_sm10`, `ch7_sm2`, `ch7_sm5`, `ch7_sm7`): the warp reached the table slot, not necessarily a useful scene.
  - Ending branches: the code selects FMV 0x2C, 0x37 or 0x38 from 0x8009AE6C and 0x8009AE40, and all three warps reach an FMV and the staff roll, but no run compared which FMV played.
  - Voice clips and music after a file moves: file-relative by static read; the shifted-disc warp checks pictures only.
- **Facts to carry:**
  - **`work/tree` must stay the pristine unpack:** the identity test rebuilds from it. Phase 5/7 builds must put edited files in a copy and point a layout at it, or `tools/check.py` fails.
  - `tools/build.py` writes one .bin with both tracks, but the player's dump has two. Phase 9 must split at track 1's end (the cue's track 2 INDEX 00) and patch track 1 only, so the player keeps track 2 and their cue.
  - File growth changes frame timing everywhere (seek time), so same-frame pixel diffs against the original don't work; a battle can even play out differently. Compare by scene.
  - `tools/*/` is gitignored, so a fresh clone needs the tools refetched: see `AGENTS.md`. `work/` too: rerun `python -X utf8 tools/unpack.py`; survey with `tools/gfx_sweep.py`, `tools/fmv_sample.py` (needs `work/jp.idx`). `work/saves/ch1_save.mcd` comes from `warp_all.py save_game`.
  - Orca runs: nested workers are refused, so use `codex exec` for independent reads (`codex exec --skip-git-repo-check --sandbox read-only -i a.png ... -- "prompt"`).
  - **There is no OPTION screen** (`docs/re/graphics.md`): the title has START and LOAD only.
  - `warp.lua` holds each overlay's table address and first word. If phase 7 moves the tables or changes their contents, update `TABLES` there and in `tools/debug/gen_scenes.py`, then regenerate `scenes.tsv`.
  - Full warp run takes about 15 minutes at `--jobs 5`, longer if other emulators share the machine.
  - `README.md` is still the template with placeholders; fill it at release (phase 9).
- **Waiting on the user (non-blocking, defaults in force):**
  - FMVs (57 videos, ~21 min of spoken Japanese, no text on screen). Subtitling means re-encoding video with jPSXdec, and the disc's streams must keep their timing. Default: leave unsubtitled for v1.0, list it in the README as a known limit; revisit after phase 9 if time remains.
  - Voiced lines stay Japanese audio under English text.
  - `奉` on the shrine box in chapter 1 map art (`docs/re/graphics.md`): default leave as scenery, since D5 names titles, menus, banners and cards.
  - Character names marked "(check)" in `glossary.md` get best-effort sources in phase 6.
