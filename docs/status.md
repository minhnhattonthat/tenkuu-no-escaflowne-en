# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1 done; next is 2 (debug tool). No build yet.
- **Done:**
  - Step 0: dump pinned, tools fetched (`AGENTS.md` lists versions and URLs), hook and check active, guard proven, original boots to title on real BIOS.
  - Phase 1: `docs/re/` holds encoding, opcodes, references, text ranges, engine, free-space candidates, LZ codec, graphics survey. Start at `docs/re/README.md`.
- **Next (phase 2):** `tools/debug/` warp to every scene from cold boot.
  - Find the caller of the scene-select string (`docs/re/disc.md`, end), and try to reach it by RAM poke. A menu per chapter would cover most of the list.
  - Scene list must include OPTION, LOAD/SAVE, partner menu, a choice box, a battle of each type, game over, all 7 chapter cards, credits. Those also confirm `docs/re/graphics.md` at runtime.
  - Then phase 3: identity rebuild with mkpsxiso. Check that overlays are found by name, not hardcoded LBA.
- **Open bugs:** none (no build).
- **Not verified:** keyboard input in the PCSX-Redux GUI (Step 0 asks for it): this run is headless, nobody pressed a key. Scripted input and Lua are proven.
- **Facts to carry:**
  - `tools/*/` is gitignored, so a fresh clone needs the tools refetched: see `AGENTS.md`. `work/` too: rerun `python -X utf8 tools/unpack.py`; survey with `tools/gfx_sweep.py`, `tools/fmv_sample.py` (needs `work/jp.idx`).
  - Orca runs: nested workers are refused, so use `codex exec` for independent reads (`codex exec --skip-git-repo-check --sandbox read-only -i a.png ... -- "prompt"`).
  - Title menu is a vertical list; cursor routes need checking (`work/qa/t_opt` went to the LOAD/EXIT window, not OPTION).
  - `README.md` is still the template with placeholders; fill it at release (phase 9).
- **Waiting on the user (non-blocking, defaults in force):**
  - FMVs (57 videos, ~21 min of spoken Japanese, no text on screen). Subtitling means re-encoding video with jPSXdec, and the disc's streams must keep their timing. Default: leave unsubtitled for v1.0, list it in the README as a known limit; revisit after phase 9 if time remains.
  - Voiced lines stay Japanese audio under English text.
  - `奉` on the shrine box in chapter 1 map art (`docs/re/graphics.md`): default leave as scenery, since D5 names titles, menus, banners and cards.
  - Character names marked "(check)" in `glossary.md` get best-effort sources in phase 6.
