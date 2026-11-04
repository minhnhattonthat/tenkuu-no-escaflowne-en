"""warp_all's pass/fail rule on run logs, and the scene list's shape (every scene it can name must be well formed)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("warp_all", ROOT / "tools" / "debug" / "warp_all.py")
warp_all = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warp_all)


def test_log_without_overlay_fails():
    assert warp_all.check_log({"chapter": "1", "expect": "-"}, "1424 title idle\n")


def test_title_scene_needs_only_title():
    assert warp_all.check_log({"chapter": "0", "expect": "-"}, "1424 title idle\n") == ""


def test_wrong_scene_word_fails_and_last_word_counts():
    log = "1460 overlay present\n1500 chapter=1 scene=0\n1800 chapter=1 scene=14\n"
    assert warp_all.check_log({"chapter": "1", "expect": "14"}, log) == ""
    assert warp_all.check_log({"chapter": "1", "expect": "0"}, log)


def test_scene_list_is_well_formed():
    rows = warp_all.scene_table()
    names = [r["name"] for r in rows]
    assert len(names) == len(set(names))
    for r in rows:
        assert 0 <= int(r["chapter"]) <= 7
        int(r["scene"]), int(r["frames"])
        if r["jump"] != "-":
            assert 0x80000000 <= int(r["jump"], 16) < 0x80200000
    # The list the skill and docs/status.md require: every card, title LOAD, game over, credits, one battle per type.
    for need in ["title_load", "save_menu", "partner_menu", "choice_box", "game_over", "credits"]:
        assert need in names
    for c in range(1, 8):
        assert f"ch{c}_card" in names
    assert {"type 0", "type 1", "type 2", "type 3"} <= {" ".join(r["proof"].split()[-2:]) for r in rows}
