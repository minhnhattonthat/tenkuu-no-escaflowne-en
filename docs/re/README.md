# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| `disc.md` | Disc layout, files, load addresses, prior work, identity build, file lookup by name | verified (dump, RAM dumps, `tests/test_identity.py`, shifted-disc warp) |
| `text.md` | Encoding, control codes, string references, text ranges | verified (`tests/test_extract.py`); dead strings static read only |
| `engine.md` | Text renderer, window fields, the VWF hook, width gate | verified (`tests/test_vwf.py`, full marker warp, `tools/debug/width_gate.py`) |
| `free-space.md` | RAM and disc room for English and hook code | the hook's three areas trap-tested; the rest candidates |
| `compression.md` | Game LZ codec | decoder verified on 15,207 TIMs; encoder not written |
| `graphics.md` | Graphics-text survey (every image with text) | static sweep done; runtime confirmation left to phase 2 warps |
| `warp.md` | Game flow, chapter and scene words, debug tool | verified by warps from cold boot (`tools/debug/warp_all.py`) |

Recon helpers: `tools/mips.py` (disassembly, lui/addiu xref, hex), `tools/sjis_scan.py`, `tools/text_recon.py`,
`tools/ramfind.py`, `tools/timscan.py`, `tools/gfx_sweep.py`, `tools/fmv_sample.py`, `tools/cdcalls.py`, `tools/lua/drawlog.lua`.
