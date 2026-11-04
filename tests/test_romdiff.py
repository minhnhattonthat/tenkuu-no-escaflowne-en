"""Nothing is written outside what the build means to touch: each overlay's bytes against its write log, the EXE against
data/exe_ranges.txt (armips patches it, so it has no log). Builds its own files, never reads work/en."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402
import romdiff  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not (extract.TREE / insert.EXE).is_file() or not insert.ARMIPS.is_file():
        pytest.skip("no work/tree or armips: run tools/unpack.py and fetch the tools")
    out = tmp_path_factory.mktemp("en")
    insert.insert(out=out, mode="en", quiet=True)
    return out


def changed_files(built):
    logs = {}
    for ln in (built / "writes.txt").read_text(encoding="utf-8").splitlines():
        name, off, old, new, by = ln.split(" ", 4)
        logs.setdefault(name, []).append((int(off, 16), bytes.fromhex(old), bytes.fromhex(new), by))
    return logs


def test_overlays_change_only_what_their_write_log_says(built):
    logs = changed_files(built)
    assert len(logs) == 9  # BATTLE + SYO00-SYO07: every program holding text was rewritten
    for name, writes in logs.items():
        rel = extract.tree_path(name)
        orig = (extract.TREE / rel).read_bytes()
        # a vacate blanks a string's old span, and text may later land on it: allowed bytes, not an overlap
        vacated = [w for w in writes if w[3].startswith("vacate")]
        assert all(orig[off:off + len(old)] == old for off, old, _new, _by in vacated), name
        allowed = {i for off, old, _new, _by in vacated for i in range(off, off + len(old))}
        errs, _n = romdiff.check(orig, (built / rel).read_bytes(), allowed, [w for w in writes if w not in vacated])
        assert not errs, name + "\n" + "\n".join(errs[:20])


def test_exe_changes_only_inside_its_allowed_ranges(built):
    allowed = set()
    for ln in (ROOT / "data/exe_ranges.txt").read_text(encoding="utf-8").splitlines():
        if ln.split("#")[0].strip():
            lo, hi = ln.split("#")[0].split("-")
            allowed.update(range(int(lo, 16), int(hi, 16) + 1))
    orig, new = (extract.TREE / insert.EXE).read_bytes(), (built / insert.EXE).read_bytes()
    errs, n = romdiff.check(orig, new, allowed, [])
    assert not errs, "\n".join(errs[:20])
    assert n > 0
    stray = bytearray(new)
    stray[0x100] ^= 1  # outside every range: the check must notice
    assert romdiff.check(orig, bytes(stray), allowed, [])[0]


def test_no_japanese_in_any_en(built):
    import re
    from batches import docs
    jp = re.compile(r"[぀-ヿ一-鿿]")
    keep = {"numbers", "debug"}
    bad = [e["id"] for d in docs().values() for e in d["entries"] if "en" in e and e.get("form") not in keep and jp.search(e["en"])]
    assert not bad, bad[:20]
    # the other way: Japanese with no English only where it can't show (SYO00's debug labels are fullwidth Latin)
    silent = [e["id"] for d in docs().values() for e in d["entries"] if "en" not in e and jp.search(e["jp"]) and not e.get("dead")]
    assert not silent, silent[:20]


def test_memory_card_title_is_english_shift_jis(built):
    new = (built / insert.EXE).read_bytes()
    assert new[0x6FC84:0x6FC84 + 21] == "ＥＳＣＡＦＬＯＷＮＥ".encode("cp932") + b"\0"


def test_romdiff_itself():
    assert subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools/romdiff.py"), "--selftest"], stdout=subprocess.DEVNULL) == 0
