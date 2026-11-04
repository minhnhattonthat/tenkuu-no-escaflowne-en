# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2 done; next is 3 (identity build). No build yet.
- **Done:**
  - Step 0: dump pinned, tools fetched (`AGENTS.md` lists versions and URLs), hook and check active, guard proven, original boots to title on real BIOS.
  - Phase 1: `docs/re/` holds encoding, opcodes, references, text ranges, engine, free-space candidates, LZ codec, graphics survey. Start at `docs/re/README.md`.
  - Phase 2: `tools/debug/warp_all.py` reaches 145 scenes from cold boot by RAM poke, on the original disc: title, LOAD, SAVE, memory-card save and load back into the saved chapter, partner menu, choice box, all 7 chapter cards and scene menus, every scene-table entry, all 43 battle sites (types 0-3), game over (direct and by losing), winning a battle, credits, 3 endings. How it works: `docs/re/warp.md`. Proof sheets read by the implementer and independently by `codex exec`; that read caught a false pass on `choice_box` and thin proofs for save and load, all fixed.
- **Next (phase 3):** identity rebuild with mkpsxiso, byte-identical to the dump, as a test. Check that overlays are found by name, not hardcoded LBA. `tools/routes/boot.txt` still works for smoke.
- **Open bugs:** none (no build).
- **Not verified:**
  - Keyboard input in the PCSX-Redux GUI (Step 0 asks for it): this run is headless, nobody pressed a key. Scripted input and Lua are proven.
  - `choice_box` pokes a real choice string into a window to prove the box draws. The game's own route to it (partner trigger, then yes/no) wasn't run, nor was picking a choice. Phase 8's story-order run covers it.
  - `battle_ch7_57` and `battle_ch7_58` show identical frames; the call sites pass different stages. Guess: shared stage data.
  - Eight tiles show a generic prompt, GAME OVER or a dark frame, so the picture can't tell which checkpoint it is (`ch1_sm5`, `ch1_sm7`, `ch2_sm3`, `ch3_sm4`, `ch5_sm10`, `ch7_sm2`, `ch7_sm5`, `ch7_sm7`): the warp reached the table slot, not necessarily a useful scene.
  - Ending branches: the code selects FMV 0x2C, 0x37 or 0x38 from 0x8009AE6C and 0x8009AE40, and all three warps reach an FMV and the staff roll, but no run compared which FMV played.
- **Facts to carry:**
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
