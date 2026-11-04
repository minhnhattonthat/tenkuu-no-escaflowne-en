"""warp_all.py: cold-boot every scene in tools/debug/scenes.tsv in parallel and check where each one landed.

  python -X utf8 tools/debug/warp_all.py [--cue CUE] [--out work/qa/warp] [--jobs 4] [--frames N] [--states] [SCENE ...]

Each run keeps <out>/<scene>/ (shots, sheet, log). A run fails on a non-zero emu.py exit, a warp that never reached
the scene (no "overlay present" or "title idle" in its log), a final scene word other than the `expect` column, or
no non-blank frame after the warp. <out>/_proof/<scene>.png is the last non-blank frame; sheets are _proof/sheet*.png.
--states writes work/states/<scene>.sstate from a passing run (regenerate after any rebuild). Exit 1 if any run fails.
"""
import argparse
import functools
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

sys.path.insert(0, str(Path(SKILL) / "scripts"))
import sheet  # noqa: E402

CUE = ROOT / "rom" / "Tenkuu no Escaflowne (Japan).cue"
BLANK_CARD = ROOT / "tools" / "pcsx" / "memcard2.mcd"  # the emulator formats it on first run; no route writes slot 2
CH1_SAVE = ROOT / "work" / "saves" / "ch1_save.mcd"


def scene_table():
    lines = (ROOT / "tools" / "debug" / "scenes.tsv").read_text(encoding="utf-8").splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


def check_log(sc, log):
    """Return an error string, or '' if the log shows the scene was reached."""
    if "overlay present" not in log and not (sc["chapter"] == "0" and "title idle" in log):
        return "never reached the overlay"
    words = re.findall(r"chapter=(-?\d+) scene=(-?\d+)", log)
    if sc["expect"] != "-" and (not words or words[-1][1] != sc["expect"]):
        return f"scene word {words[-1][1] if words else '?'}, expected {sc['expect']}"
    if sc.get("say", "-") != "-" and not re.search(r"\d+ say ", log):
        return "string was never queued (window array freed?)"
    return ""


def proof_frame(out, log):
    """The last non-blank shot after the warp landed, or None. A title frame from before the warp proves nothing."""
    m = re.search(r"(\d+) (?:overlay present|title idle)", log)
    start = int(m.group(1)) if m else 0
    shots = [out / "final.png"] + sorted(out.glob("f*.png"), reverse=True)
    for png in shots:
        n = re.match(r"f(\d+)", png.stem)
        if png.exists() and (not n or int(n.group(1)) > start) and not sheet.is_blank(sheet.read_png(png)):
            return png
    return None


@functools.cache
def vamap(cue):
    """{old string address: new}, from the .vamap tools/build.py writes beside a build that moved text."""
    p = Path(cue).with_suffix(".vamap")
    return dict(ln.split("\t") for ln in p.read_text().splitlines()) if p.exists() else {}


def run(a, sc):
    name = sc["name"]
    out = Path(a.out) / name
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "emu.py"), str(a.cue), "--out", str(out),
           "--script", str(ROOT / "tools" / "debug" / "warp.lua"), "--var", f"SCENE='{name}'",
           "--var", f"ROOT='{ROOT.as_posix()}/'", "--frames", str(a.frames or int(sc["frames"])),
           "--shot-every", str(a.shot_every), "--sheet", "--timeout", str(a.timeout)]
    if sc.get("say", "-") != "-" and sc["say"] in vamap(a.cue):
        cmd += ["--var", f"SAY={vamap(a.cue)[sc['say']]}"]
    for s in a.script:
        cmd += ["--script", s]
    for v in a.var:
        cmd += ["--var", v]
    if a.debugger:
        cmd.append("--debugger")
    if sc["mash"] == "1":
        cmd += ["--mash", "60", "--mash-key", "circle"]
    # A fresh card per run: the emulator's portable card persists, so one run's save would change another's LOAD screen.
    cmd += ["--sav", str(CH1_SAVE if name == "load_game" else BLANK_CARD)]
    if a.states:
        cmd += ["--state-out", str(ROOT / "work" / "states" / f"{name}.sstate")]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (out / "log.txt").read_text(encoding="utf-8", errors="replace") if (out / "log.txt").exists() else ""
    err = f"emu exit {p.returncode}" if p.returncode else check_log(sc, log)
    shot = proof_frame(out, log)
    if shot:
        (Path(a.out) / "_proof").mkdir(parents=True, exist_ok=True)
        shutil.copy(shot, Path(a.out) / "_proof" / f"{name}.png")
    elif not err:
        err = "every frame after the warp is blank"
    if name == "save_game" and not err and b"BISLPS" not in (out / "memcard1.mcd").read_bytes():
        err = "no save on the card"  # the last frame is the port menu either way, so the picture can't prove this
    if name == "save_game" and not err:  # the game's own save, so format and checksums are right
        CH1_SAVE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(out / "memcard1.mcd", CH1_SAVE)
    print(f"{name}: {err or 'ok'}", flush=True)
    return name, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--cue", default=str(CUE))
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "warp"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--frames", type=int)
    ap.add_argument("--shot-every", type=int, default=300)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--states", action="store_true")
    ap.add_argument("--script", action="append", default=[], help="extra Lua probe for every run")
    ap.add_argument("--var", action="append", default=[], help="extra NAME=LUA for the probe")
    ap.add_argument("--debugger", action="store_true", help="for probes that set breakpoints")
    a = ap.parse_args()
    table = scene_table()
    if a.scenes:
        known = {r["name"] for r in table}
        for s in a.scenes:
            if s not in known:
                sys.exit(f"unknown scene: {s}")
        table = [r for r in table if r["name"] in a.scenes]
    first = [r for r in table if r["name"] == "save_game"]  # load_game reads the card this one writes
    res = [run(a, r) for r in first]
    with ThreadPoolExecutor(a.jobs) as ex:
        res += list(ex.map(lambda r: run(a, r), [r for r in table if r not in first]))
    bad = [r for r in res if r[1]]
    print(f"{len(res) - len(bad)}/{len(res)} ok")
    for n, e in bad:
        print(f"FAIL {n}: {e}")
    subprocess.run([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "sheet.py"),
                    *(str(Path(a.out) / "_proof" / f"{r['name']}.png") for r in table
                      if (Path(a.out) / "_proof" / f"{r['name']}.png").exists()),
                    "--max", "30", "--cols", "6", "--out", str(Path(a.out) / "_proof" / "sheet.png")], check=False)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
