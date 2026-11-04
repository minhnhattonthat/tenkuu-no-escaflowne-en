"""Nothing is written outside what the build means to touch: each overlay's bytes against its write log, the EXE against
data/exe_ranges.txt (armips patches it, so it has no log). Every rewritten ref resolves, no reader is left behind, every
table is written whole, no hook swallows a branch target. Builds its own files, never reads work/en."""
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dte  # noqa: E402
import extract  # noqa: E402
import font  # noqa: E402
import insert  # noqa: E402
import jptext  # noqa: E402
import romdiff  # noqa: E402

EXE_BASE = 0x8000F800
# 4 sites pass the next overlay's entry point to the loader; it only lands inside this overlay's script (docs/re/text.md)
LOADER_SITES = {("SYO02", 0x800D4598), ("SYO03", 0x800D92F4), ("SYO05", 0x800D0AD4), ("SYO06", 0x800D2C88)}
TITLE_OFF, RESETGRAPH_STRING_OFF = 0x6FC84, 0x252C


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


def overlay_logs(built):
    return {n: w for n, w in changed_files(built).items() if n != "SLPS_010"}


def exe_ranges():
    """[(lo, hi)] file offsets, hi exclusive."""
    out = []
    for ln in (ROOT / "data/exe_ranges.txt").read_text(encoding="utf-8").splitlines():
        if ln.split("#")[0].strip():
            lo, hi = ln.split("#")[0].split("-")
            out.append((int(lo, 16), int(hi, 16) + 1))
    return out


def own_refs(name, e):
    """An entry's refs in this overlay: a shared entry lists all eight."""
    return [r for r in e.get("refs", ()) if r.get("file", name + ".BIN") in (f"{name}.BIN", insert.tree_name(name))]


def wants_bytes(e):
    fnt = font.Font()
    return insert.text_of(e, "en", {}, fnt, insert.LINE_PX) is not None and not (e.get("dead") and e.get("no_end"))


def overlays():
    return {n: es for n, es in insert.load_entries().items() if n != "SLPS_010"}


def written_reg(x):
    """The register an instruction writes, or None."""
    op, rs, rt, rd = x >> 26, (x >> 21) & 31, (x >> 16) & 31, (x >> 11) & 31
    if op == 0:
        return rd
    if op == 3:
        return 31
    if 8 <= op <= 15 or 0x20 <= op <= 0x26 or (op in (0x10, 0x12) and rs in (0, 2)):
        return rt
    return None


def strict_pairs(d):
    """(index of the low instruction, target): stops at any write to the register, so reads through a loaded pointer don't count."""
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    for i, w in enumerate(words):
        if w >> 26 != 0x0F or not (w >> 16) & 31:
            continue
        rt = (w >> 16) & 31
        for j in range(i + 1, min(i + 17, n)):
            x = words[j]
            op, rs = x >> 26, (x >> 21) & 31
            if rs == rt and op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                low = x & 0xFFFF
                low = low if op == 0x0D else (low - 0x10000 if low & 0x8000 else low)
                yield j, ((w & 0xFFFF) << 16) + low & 0xFFFFFFFF
            if written_reg(x) == rt:
                break


def text_spans(entries):
    return [(int(e["off"], 16), int(e["off"], 16) + e["size"]) for e in entries]


def inside(spans, o):
    return any(a <= o < b for a, b in spans)


def test_overlays_change_only_what_their_write_log_says(built):
    logs = overlay_logs(built)
    assert len(logs) == 9  # BATTLE + SYO00-SYO07: every program holding text was rewritten
    for name, writes in logs.items():
        rel = extract.tree_path(name)
        orig, new = (extract.TREE / rel).read_bytes(), (built / rel).read_bytes()
        # a vacate blanks a string's old span, and text may later land on it: allowed bytes, not an overlap
        vacated = [w for w in writes if w[3].startswith("vacate")]
        assert all(orig[off:off + len(old)] == old for off, old, _new, _by in vacated), name
        allowed = {i for off, old, _new, _by in vacated for i in range(off, off + len(old))}
        errs, _n = romdiff.check(orig, new, allowed, [w for w in writes if w not in vacated])
        assert not errs, name + "\n" + "\n".join(errs[:20])
        # a vacated byte is either blank or part of a text write: nothing else may hide in those spans
        covered = {i for off, _old, data, by in writes if by.startswith("text") for i in range(off, off + len(data))}
        stray = [hex(i) for i in allowed - covered if new[i]]
        assert not stray, f"{name}: {stray[:20]}"


def test_exe_changes_only_inside_its_allowed_ranges(built):
    allowed = {i for lo, hi in exe_ranges() for i in range(lo, hi)}
    orig, new = (extract.TREE / insert.EXE).read_bytes(), (built / insert.EXE).read_bytes()
    errs, n = romdiff.check(orig, new, allowed, [])
    assert not errs, "\n".join(errs[:20])
    assert n > 0
    stray = bytearray(new)
    stray[0x100] ^= 1  # outside every range: the check must notice
    assert romdiff.check(orig, bytes(stray), allowed, [])[0]


def test_every_rewritten_ref_resolves_to_its_string(built):
    jp, dt = jptext.Jp(), dte.Dte()
    logs, checked = overlay_logs(built), 0
    for name, entries in overlays().items():
        rel, base = extract.tree_path(name), extract.base_of(name)
        orig, new = (extract.TREE / rel).read_bytes(), (built / rel).read_bytes()
        lui_of = insert.lui_map(orig)
        at = {by.split()[1]: off for off, _old, _new, by in logs[name] if by.startswith("text ")}
        for e in entries:
            if not wants_bytes(e):
                continue
            data = insert.encode(e.get("en", e["jp"]), jp, dt)
            assert new[at[e["id"]]:at[e["id"]] + len(data)] == data, e["id"]
            for r in own_refs(name, e):
                site, want = int(r["site"], 16) - base, base + at[e["id"]] + r["delta"]
                word = struct.unpack_from("<I", new, site)[0]
                if r["kind"] == "word":
                    got = word
                else:
                    hi = struct.unpack_from("<I", new, lui_of[site // 4] * 4)[0] & 0xFFFF
                    lo = word & 0xFFFF
                    got = (hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo) & 0xFFFFFFFF
                assert got == want, f"{name} {r['site']} {e['id']}: {got:#x}, want {want:#x}"
                checked += 1
    assert checked > 3000


def test_relocated_strings_leave_no_reader_behind(built):
    found = set()
    for name, entries in overlays().items():
        base = extract.base_of(name)
        orig = (extract.TREE / extract.tree_path(name)).read_bytes()
        moved = [e for e in entries if wants_bytes(e)]
        spans = text_spans(entries)
        olds = sorted((base + int(e["off"], 16), base + int(e["off"], 16) + e["size"]) for e in moved)
        known = {int(r["site"], 16) for e in moved for r in own_refs(name, e)}
        starts = {a for a, _b in olds}

        def is_old(t):
            return any(a <= t < b for a, b in olds)

        for j, target in strict_pairs(orig):
            if is_old(target) and base + j * 4 not in known and not inside(spans, j * 4):
                found.add((name, base + j * 4))
        for o in range(0, len(orig) - 3, 4):
            if not inside(spans, o) and base + o not in known and struct.unpack_from("<I", orig, o)[0] in starts:
                found.add((name, base + o))
    # equal, not a subset: finding the 4 known false refs is what proves the scan still sees readers
    assert found == LOADER_SITES, sorted((n, hex(s)) for n, s in found ^ LOADER_SITES)


def test_every_table_writes_all_its_entries(built):
    logs = overlay_logs(built)
    for name, entries in overlays().items():
        wanted = {e["id"] for e in entries if wants_bytes(e)}
        written = {by.split()[1] for _o, _old, _new, by in logs[name] if by.startswith("text ")}
        assert written == wanted, f"{name}: {sorted(wanted ^ written)[:20]}"
        words = [by for _o, _old, _new, by in logs[name] if by.startswith("word ")]
        assert len(words) == sum(r["kind"] == "word" for e in entries if wants_bytes(e) for r in own_refs(name, e)), name
        if name in extract.SCRIPTS:
            names = {e["id"] for e in entries if e.get("form") == "name"}
            assert len(names) == 49 and sum(by.split()[1] in names for by in words) == 49, name


def branch_target(word, site):
    op = word >> 26
    if op in (2, 3):
        return (site & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
    if op in (1, 4, 5, 6, 7):
        imm = word & 0xFFFF
        return (site + 4 + ((imm - 0x10000 if imm & 0x8000 else imm) << 2)) & 0xFFFFFFFF
    return None


def test_no_hook_swallows_a_branch_target():
    """Whole EXE, and j/jal in every overlay's code: nothing lands strictly inside a span the hook overwrites."""
    if not (extract.TREE / insert.EXE).is_file():
        pytest.skip("no work/tree")
    spans = [(lo + EXE_BASE, hi + EXE_BASE) for lo, hi in exe_ranges()]
    exe = (extract.TREE / insert.EXE).read_bytes()
    hits = []
    for o in range(0x800, len(exe) - 3, 4):
        site = o + EXE_BASE
        t = branch_target(struct.unpack_from("<I", exe, o)[0], site)
        if t is not None and not any(a <= site < b for a, b in spans):
            hits += [(insert.EXE, site, t) for a, b in spans if a < t < b]
    for name, entries in overlays().items():
        base, text = extract.base_of(name), text_spans(entries)
        d = (extract.TREE / extract.tree_path(name)).read_bytes()
        for o in range(0, len(d) - 3, 4):
            w = struct.unpack_from("<I", d, o)[0]
            if w >> 26 in (2, 3) and not inside(text, o):
                t = branch_target(w, base + o)
                hits += [(name, base + o, t) for a, b in spans if a < t < b]
    assert not hits, [(n, hex(s), hex(t)) for n, s, t in hits[:20]]


def test_no_japanese_in_any_en(built):
    from batches import docs
    jp = re.compile(r"[぀-ヿ一-鿿]")
    keep = {"numbers", "debug"}
    bad = [e["id"] for d in docs().values() for e in d["entries"] if "en" in e and e.get("form") not in keep and jp.search(e["en"])]
    assert not bad, bad[:20]
    # the other way: insert.py writes `jp` back for an entry with no `en`, so only a head that takes no bytes may lack one
    silent = [e["id"] for d in docs().values() for e in d["entries"]
              if "en" not in e and jp.search(e["jp"]) and not (e.get("dead") and e.get("no_end"))]
    assert not silent, silent[:20]


def test_memory_card_title_is_english_shift_jis_and_logged(built):
    new = (built / insert.EXE).read_bytes()
    title = "ＥＳＣＡＦＬＯＷＮＥ".encode("cp932") + b"\0"
    assert new[TITLE_OFF:TITLE_OFF + 21] == title
    orig = (extract.TREE / insert.EXE).read_bytes()
    assert [(TITLE_OFF, orig[TITLE_OFF:TITLE_OFF + 21], title)] == [w[:3] for w in changed_files(built)["SLPS_010"]]


def test_hook_leaves_no_format_specifier_where_resetgraph_prints(built):
    new = (built / insert.EXE).read_bytes()
    assert b"%" not in new[RESETGRAPH_STRING_OFF:new.index(b"\0", RESETGRAPH_STRING_OFF)]


def test_romdiff_itself():
    assert subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools/romdiff.py"), "--selftest"], stdout=subprocess.DEVNULL) == 0
