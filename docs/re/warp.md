# Warp: how the debug tool reaches every scene

`tools/debug/warp.lua` pokes RAM only: no disc change, no save needed, so the same script works on the original and on every build. Scene list: `tools/debug/scenes.tsv`, written by `tools/debug/gen_scenes.py`. All scenes: `python -X utf8 tools/debug/warp_all.py`. Static map of every chapter: `python -X utf8 tools/syo_map.py`.

## Game flow (verified: code read and warps)

- **SYO00 is the master overlay.** Entry 0x800C4920 calls the title loop 0x800C46D0, which waits for **0x8009AE34** (title result): 1 START, 2 LOAD, -1 attract again. Then it reads the chapter and loads `SYOnn` through a jump table.
- **Chapter word 0x8009AE68, scene word 0x8009AE28.** Save data holds these plus 0x8009AE6C and 0x8009AE40 (0x8001E1D8). Those two halfwords are compared at the ending (0x800D6884): both negative or equal → FMV 0x2C, AE6C < AE40 → 0x37, else 0x38 (guess: Hitomi and Merle affection).
- **Each chapter's main** reads the scene word and switches on it (table below). 0 plays the chapter card. -1 opens the developers' scene-select menu. Other negatives are that menu's results. Positives are the checkpoints saves resume from. Anything else runs off the end: next chapter (chapter+1, scene 0, save prompt 0x800C4E38, then `0x80037904` to load it).
- **Scene word as written during play** often has no table slot (chapter 1 writes 5, 0xD, 0xF…), so it is progress bookkeeping, not always a resume point.
- **Overlay slots:** 0x80014E40(n) loads n to 0x801D8000: 0 MOVIE, 1 BATTLE, 2 TITLE, 3 STAFF. MOVIE entry 0x801D8570(fmv id), TITLE chapter card 0x801D8B28(chapter), BATTLE 0x801D9478(stage), STAFF 0x801D8C58.
- **Tasks:** 0x80016124(id) kills a task, 0x8001637C(id) finds it. Title menu is task 0x82, battle 0xA1.

| Chapter | Entry | Table (index = scene+10) |
|---|---|---|
| 1 | 0x800DB6E4 | 0x800C440C |
| 2 | 0x800D3D80 | 0x800C321C |
| 3 | 0x800D8D2C | 0x800C2D9C |
| 4 | 0x800DD3B4 | 0x800C2D8C |
| 5 | 0x800D032C | 0x800C29EC |
| 6 | 0x800D269C | 0x800C2C0C |
| 7 | 0x800D5CA4 | 0x800C2EE4 |

## The warp

1. Press circle on the title until the title result goes non-zero. **It must be a real press.** The title's handler 0x801D8F34 also kills its own task (0x82). A poke leaves the task alive, BATTLE.BIN loads over its code, and the emulator hangs with no more vsyncs (three 900 s timeouts before this was found). Cards and menus survived the poke only because they load TITLE.BIN back into the same place.
2. Every frame, write chapter and scene. SYO00 writes chapter=1/scene=0 and then waits two vsyncs (0x800C478C) before reading them, so the poke wins.
3. A `jump` scene writes its target into the table slot for its scene word while the overlay loads, and keeps rewriting it for 600 frames. Main reads the slot only after the whole file arrives. One write is not enough: chapter 6's table (file 0xFE4) straddles a sector, so the first word arrives before the slot and the later sector overwrites it. The table's first word tells that the overlay arrived.

The title result word and chapter word are the only ones that need timing. On a build where overlay sizes change, check `TABLES` in `warp.lua`: its addresses come from the overlay, not the disc.

## Scene types

- **`chN_card`, `chN_menu`, `chN_sM`:** the scene word as above. `m` means negative. Chapter entries use scene 0, the way the game enters them after the previous chapter.
- **`battle_chN_S`:** jump to the `jal` of that battle's routine in main. Stage is the argument of 0x801D9478. Type is the value in 0x8009AE48 (0-3).
- **`game_over`:** jump to main's call of 0x800C55D0, which unpacks `GAME OVER` from the overlay. **`lose_battle`:** real path, HP poked to 0, battle routine returns -1, main calls it.
- **`save_menu`:** 0x800C4E38, the chapter-end save prompt. **`title_load`:** route presses down and circle on the title, 150 frames after it goes idle (earlier presses are dropped during its fade-in).
- **`save_game`, `load_game`:** the game writes a real save to a fresh card, which `warp_all.py` keeps as `work/saves/ch1_save.mcd` (holds no RAM pointers, so it survives rebuilds; regenerate by running `save_game`). `load_game` reads it from the title and walks the LOAD messages. Every other run gets a blank card, since the emulator's portable card persists between runs.
- **`free_roam`, `partner_menu`:** jump to chapter 1's first free-roam routine 0x800CA6B8; triangle (pad bit 0x10) opens the partner menu in 0x800C5AD8. That routine compares the player's position with trigger rectangles from a table in a1.
- **`choice_box`:** queues a real choice string (`say` column, VA) into a text window, the same write `0x80039760(window, string)` does: `w + 0x68 + 4*count = string`, `w + 0x5E = count+1`, `w + 0x518 = 0`, with `w = *(gp+0x16C) + index*0x7DC`. **The window array exists only while text is open:** the pointer is 0 before the first text and again after the text closes (verified by probe), so the route opens the partner menu and leaves it open. This shows any string in any window, so phase 5 can use it to measure box widths. It proves the box draws, not the choice's own flow: the game reaches this string at 0x800CD750 (routine 0x800CCF40, called from main 0x800DB8F4) after a yes/no in 0x800C59E8, gated on a mask in task 0xE9's data (0x800CD6DC) whose source is not traced. Read from the code, not run. The story-order run (phase 8) covers the real path.
- **`credits`, `ending_*`:** jump into chapter 7's end (0x800D6910, 0x800D687C). Endings poke 0x8009AE6C and 0x8009AE40.

**Battle state (verified by poke and log, `lose_battle`, `win_battle`):** `*0x801F7B20` + 0x138 player HP, + 0x13A max (log reads 400/400), + 0x288 enemy HP. HP 0 gives GAME OVER and then a reset to the logo; enemy HP 0 moves on to the next stage. `GOD=1` or the `god` flag pins player HP; all `battle_*` scenes use it, because some stages (56, 66) inherit HP from the stage before and a warp starts them at 0. `win` and `lose` flags poke 900 frames after the warp.

## Not reachable, by reading the code

**OPTION:** the title's cursor word `w+0x6500` is only ever set to 0 (up) or 1 (down) (0x801DA02C, 0x801DA05C) and only 0 and 1 are handled (0x801D8FAC-0x801D9008). Art for an OPTION label exists but no code path shows it. Nothing to translate unless the label appears on screen; see the `title` proof.

## Limits

- `warp_all.py` proves a warp three ways: the log shows the overlay arrived, the scene word matches `expect` where it is set, and a frame after the warp isn't blank. A `say` scene must also log its queue, and `save_game` must leave a save on the card. None of that proves the picture is right: read `work/qa/warp/_proof/sheet*.png`, and an independent read of them caught the first `choice_box` passing with no window on screen (its proof was byte-identical to `free_roam`). `sha1sum _proof/*.png | sort | uniq -w40 -D` finds such duplicates fast.
- Some `chN_sM` scenes land on the save prompt or a black frame between FMVs, since their table slot is simply where that menu entry resumes. Those still prove the entry point. Duplicates of this kind: `ch7_sm7` = `game_over`; `ch2_sm3`, `ch7_sm5` = `save_menu`; `ch1_sm7`, `ch5_sm10` = `save_game`.
- `battle_ch7_57` and `battle_ch7_58` give byte-identical frames at every shot, though their call sites pass different stages (0x39, 0x3A) and set different scene words. Guess: the stages share data. Not checked.
- `win_battle`'s proof is the story text after the battle: the win is shown by the log (enemy HP 0, then scene 14 → 16), not by the frame. `save_game`'s last frame is the port menu it returns to after saving; the card check proves the save.

- `jump` starts mid-chapter with flags at their cold-boot defaults, so a scene gated on earlier flags can take its other branch. Fine for reading text; the story-order run is the playtest (phase 8).
- Portraits and map art for a jump scene come from whatever the routine itself loads. Routines that assume a previous routine loaded data may draw wrong. Note any such case here.
