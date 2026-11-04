"""width_gate.py: stress build for the width gate: digit rulers in each box variant, and the glyph torture line.

    python -X utf8 tools/debug/width_gate.py [--out work/qa/gate]

Rulers of digits show how far a row reaches; font.width gives each ruler's pixels. Results: data/windows.json.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import font  # noqa: E402
import insert  # noqa: E402

SCENES = ["ch1_sm10", "choice_box", "partner_menu", "title_load", "title_load_confirm", "save_menu", "save_confirm",
          "battle_ch1_1", "load_game", "save_game"]
TOKEN_RUN = r"((?:\{[^}]*\})+)$"


def ruler(px):
    """Digits up to exactly px wide or just under."""
    fnt, out = font.Font(), ""
    for c in "0123456789" * 8:
        if fnt.width(out + c) > px:
            break
        out += c
    return out


def torture(fnt, px=170):
    """Every printable ASCII character plus double spaces, one page of lines at most px wide."""
    lines, cur = [], ""
    for c in "".join(chr(c) for c in range(0x21, 0x7B)) + "|}~  a  b":  # no "{": it opens a token in script text
        if fnt.width(cur + c) > px:
            lines.append(cur)
            cur = ""
        cur += c
    return lines + [cur]


def dialogue(jp, body):
    """The entry's own name tag and closing codes around new body text."""
    head = re.match(r".*?\{nameoff\}\{color\d\}\{nl2?\}", jp).group(0)
    return head + body + re.search(TOKEN_RUN, jp).group(1)


def qa_entries():
    entries = {e["id"]: e for doc in ("SYO01", "common")
               for e in json.loads((ROOT / f"script/{doc}.json").read_text(encoding="utf-8"))["entries"]}
    r = ruler(224)
    tl = torture(font.Font())
    qa = {
        "syo01_248": dialogue(entries["syo01_248"]["jp"], "W" * 28 + "{nl}" + ruler(209)),  # 223 px: the last pixel column
        "syo01_249": dialogue(entries["syo01_249"]["jp"], "{wait}{clear}{nl2}".join(
            "{nl}".join(tl[i:i + 2]) for i in range(0, len(tl), 2))),
        "syo01_258": dialogue(entries["syo01_258"]["jp"].replace("メルル", "Hitomi's Grandmother (young)"),
                              "{nl}".join([r, ruler(230), "row 3", "row 4"])),
        "syo01_141": entries["syo01_141"]["jp"].split("{nl2}")[0] + "{nl2}" + r + "{nl2}　　{mark1}{color4}1){color2} " + r
        + "{nl2}　　{mark2}{color4}2){color2} " + ruler(180) + "{nl2}　　{mark3}{color4}3){color2} short{nl2}"
        + "　　{mark4}{color4}4){color2} short{menuwait}{close}{nl2}{end}",
    }
    for eid in ("common_001", "common_011", "common_033"):
        jp = entries[eid]["jp"]
        marks = re.match(r"(?:\{clear\})?[　]*(?:\{mark\d+\})?[　]*", jp).group(0)
        qa[eid] = marks + ruler(224 - 12 * jp.count("　")) + re.search(TOKEN_RUN, jp).group(1)
    # the shared block has no room to spare: the messages no gate scene shows give theirs up
    for n in (*range(15, 31), *range(34, 47)):
        jp = entries[f"common_{n:03}"]["jp"]
        qa[f"common_{n:03}"] = "".join(re.findall(r"\{[^}]*\}", jp))
    return qa


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "work/qa/gate"))
    a = ap.parse_args()
    out = ROOT / "build/escaflowne_gate"
    build.build(out, 0, insert.insert(mode="marker", qa=qa_entries(), quiet=True))
    (out.with_suffix(".vamap")).write_bytes((ROOT / "work/en/vamap.tsv").read_bytes())
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools/debug/warp_all.py"), "--cue", str(out.with_suffix(".cue")),
                              "--out", a.out, "--jobs", "4", "--shot-every", "30", *SCENES]))
