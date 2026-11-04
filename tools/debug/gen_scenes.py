"""gen_scenes.py: write tools/debug/scenes.tsv from the overlays (scene tables, battle sites) plus the hand-found scenes.

Run from the repo root after `tools/unpack.py`; addresses read from an original-layout overlay.
"""
import struct
from pathlib import Path
B = 0x800C1C28
PRG = Path("work/tree/ESCA/PRG")
sext = lambda x: struct.unpack("<h", struct.pack("<H", x & 0xFFFF))[0]
TABLE = {1: (0x800C440C, 23, 10), 2: (0x800C321C, 30, 10), 3: (0x800C2D9C, 53, 10), 4: (0x800C2D8C, 85, 10), 5: (0x800C29EC, 33, 10), 6: (0x800C2C0C, 12, 10), 7: (0x800C2EE4, 67, 10)}
COLS = "name chapter scene jump frames mash route expect flags pokes say say_win say_wait proof".split()
rows = []
def add(name, chapter, scene=0, jump=None, frames=2400, mash=0, route=None, expect=None, flags=None, pokes=None, say=None, say_win=None, say_wait=None, proof="x"):
    rows.append([name, chapter, scene, hex(jump) if jump else "-", frames, mash, route or "-", "-" if expect is None else expect, flags or "-", pokes or "-", hex(say) if say else "-", "-" if say_win is None else say_win, "-" if say_wait is None else say_wait, proof])

add("title", 0, frames=2700, proof="title menu")  # the title comes up as late as frame 2027 when no mash skips the FMVs
add("opening_logo", 0, frames=4600, proof="opening video's logo, idling on the title")
add("title_load", 0, frames=2300, route="150 -;8 down;30 -;8 circle;300 -", proof="LOAD/EXIT window")
add("title_load_confirm", 0, frames=2600, route="150 -;8 down;30 -;8 circle;300 -;8 circle;300 -", proof="LOAD yes/no window")
for c in range(1, 8):
    add(f"ch{c}_card", c, 0, frames=2400, expect=0, proof="chapter card")
    add(f"ch{c}_menu", c, -1, frames=2700, expect=-1, proof="scene-select menu")
for c, (va, n, addv) in TABLE.items():
    d = (PRG / f"SYO{c:02d}.BIN").read_bytes()
    t = [struct.unpack_from("<I", d, va - B + 4 * i)[0] for i in range(n)]
    default = max(set(t), key=t.count)
    seen = {}
    for i, tgt in enumerate(t):
        s = i - addv
        if tgt == default or s in (0, -1) or tgt in seen:
            continue
        seen[tgt] = s
        name = f"ch{c}_s{'m' + str(-s) if s < 0 else s}"
        add(name, c, s, frames=3000, mash=1, proof="scene start")
    # battles: jump to the jal in main
    n4 = len(d) // 4
    w = struct.unpack("<%dI" % n4, d[:n4 * 4])
    bat = []
    for k, x in enumerate(w):
        if x == 0x0C005390 and w[k + 1] == 0x24040001:
            f = k
            while not (w[f] >> 16 == 0x27BD and w[f] & 0x8000):
                f -= 1
            sc = next((sext(w[i - 1]) for i in range(f, k) if 0), None)
            vals = {}
            regs = {}
            for i in range(f, k):
                y = w[i]
                if y >> 26 == 9 and (y >> 21) & 31 == 0:
                    regs[(y >> 16) & 31] = sext(y)
                elif y >> 26 == 0x2B and (y >> 21) & 31 == 1 and sext(y) == 0xAE28 - 0x10000:
                    r = (y >> 16) & 31
                    vals["scene"] = regs.get(r)
                elif y >> 26 == 0x2B and (y >> 21) & 31 == 1 and sext(y) == 0xAE48 - 0x10000:
                    r = (y >> 16) & 31
                    vals["type"] = regs.get(r, 0)
            j = 0x0C000000 | ((B + f * 4 & 0x0FFFFFFF) >> 2)
            caller = [B + i * 4 for i, y in enumerate(w) if y == j][0]
            stage = sext(w[k + 3])
            bat.append((caller, stage, vals))
    for caller, stage, vals in bat:
        label = f"battle_ch{c}_{stage}"
        if any(r[0] == label for r in rows):
            label += "_" + hex(caller)[-3:]
        add(label, c, 0, jump=caller, frames=3000, expect=vals.get("scene"), flags="god", proof=f"battle stage {stage} type {vals.get('type')}")
add("game_over", 1, 0, jump=0x800DB9D8, frames=2400, proof="GAME OVER")
add("lose_battle", 1, 0, jump=0x800DB9C8, frames=3250, flags="lose", proof="battle then GAME OVER")
add("win_battle", 1, 0, jump=0x800DB9C8, frames=4200, flags="win", proof="battle ends, story continues")
add("save_menu", 1, 0, jump=0x800DB980, frames=2400, proof="SAVE/EXIT window")
add("save_confirm", 1, 0, jump=0x800DB980, frames=2800, route="400 -;8 circle;300 -", proof="SAVE yes/no window")
add("save_game", 1, 0, jump=0x800DB980, frames=4200, route="400 -;8 circle;240 -;8 circle;240 -;8 circle;300 -;8 circle;300 -;8 circle;300 -;8 circle;300 -", proof="writes work/saves/ch1_save.mcd")
add("load_game", 0, frames=4400, route="150 -;8 down;30 -;8 circle;300 -;8 circle;300 -;8 circle;300 -;8 circle;300 -;8 circle;300 -;8 down;30 -;8 circle;1100 -", proof="LOAD messages, EXIT, then the saved chapter")
add("free_roam", 1, 0, jump=0x800DB834, frames=2800, proof="free roam")
add("partner_menu", 1, 0, jump=0x800DB834, frames=3000, route="600 -;8 triangle;240 -", proof="partner menu")
add("partner_pick", 1, 0, jump=0x800DB834, frames=3400, route="600 -;8 triangle;240 -;8 circle;240 -;8 circle;240 -", proof="partner menu, first row picked")
# The game's own route, from main's call of the routine that holds it (0x800CCF40): a candidate bit makes "Partner Up" ask
# (0x800C59E8); yes shows the 1)-4) box; circle picks option 1.
add("partner_prompt", 1, 0, jump=0x800DB8F4, frames=3400, flags="mask=2", route="600 -;8 triangle;240 -;8 circle;240 -;8 circle;240 -", proof="partner prompt with Hitomi's name")
add("partner_choice", 1, 0, jump=0x800DB8F4, frames=3800, flags="mask=2", route="600 -;8 triangle;240 -;8 circle;240 -;8 circle;240 -;8 circle;300 -", proof="choice box the game opened itself")
add("partner_answer", 1, 0, jump=0x800DB8F4, frames=4200, flags="mask=2", route="600 -;8 triangle;240 -;8 circle;240 -;8 circle;240 -;8 circle;300 -;8 circle;300 -", proof="first option picked")
# The real 1)-4) string (0x800DCCB2, shown by 0x800CD750 in window 1), poked while the partner menu keeps the window array alive: the array is freed when text closes.
add("choice_box", 1, 0, jump=0x800DB834, frames=3600, route="600 -;8 triangle;1500 -", say=0x800DCCB2, say_win=1, say_wait=900, proof="dialogue choice box")
add("credits", 7, 0, jump=0x800D6910, frames=18400, proof="whole staff roll")
add("ending_tie", 7, 0, jump=0x800D687C, frames=9000, pokes="0x8009AE6C=0 0x8009AE40=0", proof="ending FMV 0x2C then staff roll")
add("ending_a", 7, 0, jump=0x800D687C, frames=9000, pokes="0x8009AE6C=2 0x8009AE40=1", proof="ending FMV 0x38 then staff roll")
add("ending_b", 7, 0, jump=0x800D687C, frames=9000, pokes="0x8009AE6C=1 0x8009AE40=2", proof="ending FMV 0x37 then staff roll")
out = ["\t".join(COLS)] + ["\t".join(str(x) for x in r) for r in rows]
Path("tools/debug/scenes.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(len(rows), "scenes")
