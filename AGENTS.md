# Tenkuu no Escaflowne (PS1) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json); `python tools/skill.py` prints its folder (`$SKILL`). Read its SKILL.md before ROM, text or QA work. Never paste a `plugins/cache/<hash>` path.

## Commands (run from repo root)
- Unpack: `python -X utf8 tools/unpack.py` -> work/tree + work/layout.xml (dumpsxiso)
- Build:  `python -X utf8 tools/build.py` -> build/escaflowne_en.bin + .cue (checks the dump against `rom.sha1` first; not written until phase 3)
- Check:  `python -X utf8 tools/check.py` (tests + lint; the pre-commit hook runs this; `git config core.hooksPath tools/hooks` once per clone)
- Smoke:  `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/escaflowne_en.cue --out work/qa/smoke --route tools/routes/boot.txt --smoke`
- Warp:   `python -X utf8 tools/debug/warp_all.py --cue build/escaflowne_en.cue <scene>...` (no scene = all, `--states` saves `work/states/`; scene list `tools/debug/scenes.tsv`, how it works `docs/re/warp.md`; never ask the user to play to a scene)
- Release: `python -X utf8 tools/release.py` (patch + verify; never publish without the user; written in phase 9)
- Clean:  `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original disc: `rom/Tenkuu no Escaflowne (Japan).cue` + 2 tracks (gitignored; SHA-1s in `rom.sha1`, checked by `tools/check_rom.py`).
- Tools (gitignored, this repo's own copies; refetch with the skill's `fetch_emu.py` or the URLs):
  - `tools/pcsx/` PCSX-Redux nightly 30264.20261103.29 (`fetch_emu.py pcsx`), BIOS `tools/bios/scph5500.bin` (`fetch_emu.py psx-bios`)
  - `tools/mkpsxiso/` mkpsxiso/dumpsxiso 2.30 (github.com/Lameguy64/mkpsxiso/releases/download/v2.30/mkpsxiso-2.30-win64.zip)
  - `tools/armips/` armips 0.11.0 (github.com/Kingcom/armips/releases/download/v0.11.0/armips-v0.11.0-windows-x86.7z)
  - `tools/jpsxdec/` jPSXdec 2.1 beta (github.com/m35/jpsxdec/releases/download/v2.1/jpsxdec_v2.1-beta.zip; index: `java -jar <jar> -f <Track 1 .bin> -x work/jp.idx`)
- Savestates: `work/states/`. Text: `script/` (JSON). Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose: their short tool list cuts each agent's start-up context from ~43k to ~9k tokens. Under an Orca one-shot run nested workers are refused: do those passes yourself or with `codex exec`.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Japanese game: confirm is circle, cancel is cross (`--mash-key circle`).

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
