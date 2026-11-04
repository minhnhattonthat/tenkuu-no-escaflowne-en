"""Extraction: every committed string re-encodes to the disc's bytes, the text ranges are fully covered, non-text is marked."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract
import jptext

TREE = ROOT / "work" / "tree"
SCRIPT = ROOT / "script"
needs_tree = pytest.mark.skipif(not TREE.is_dir(), reason="no unpacked tree")


def docs():
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCRIPT.glob("*.json"))}


def entries():
    return [e for doc in docs().values() for e in doc["entries"]]


def spoken():
    return [e for e in entries() if "form" in e]


def files_of(name, doc):
    return [f"ESCA/PRG/{s}.BIN" for s in extract.SCRIPTS] if name == "common.json" else [doc["file"]]


@needs_tree
def test_every_string_roundtrips():
    jp = jptext.Jp()
    count = 0
    for name, doc in docs().items():
        for f in files_of(name, doc):
            d = (TREE / f).read_bytes()
            for e in doc["entries"]:
                o = int(e["off"], 16)
                assert jp.encode(e["jp"]) == d[o:o + e["size"]], f"{f} {e['id']}"
                count += 1
    assert count == 3501  # 2685 program entries + 102 shared entries x 8 copies


@needs_tree
def test_ranges_covered_and_no_text_outside():
    # gaps, strays by raw scan and by pointer target, the 8 shared copies, unknown tokens
    r = subprocess.run([sys.executable, "-X", "utf8", "tools/extract.py", "--check"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


@needs_tree
def test_committed_script_matches_the_disc(tmp_path):
    r = subprocess.run([sys.executable, "-X", "utf8", "tools/extract.py", "--out", str(tmp_path)], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in tmp_path.glob("*.json")) == sorted(docs())
    for name, doc in docs().items():
        fresh = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert [{k: v for k, v in e.items() if k not in ("en", "tl")} for e in doc["entries"]] == fresh["entries"], name


@needs_tree
def test_a_shrunk_range_is_caught():
    """Proves the coverage check bites: take the last strings out of chapter 1's range."""
    jp = jptext.Jp()
    ranges = extract.load_ranges()
    ranges["SYO01"] = [(a, b - 0x100 if r == "script" else b, r, n) for a, b, r, n in ranges["SYO01"]]
    d = (TREE / "ESCA/PRG/SYO01.BIN").read_bytes()
    a, b = next((a, b) for a, b, r, _n in ranges["SYO01"] if r == "script")
    with pytest.raises(ValueError):  # the cut lands inside a string, and walk refuses it
        extract.walk(d, jp, a, b)
    end = max(o + s for o, s, _t, _k in extract.walk(d, jp, a, d.rfind(b"\0", 0, b) + 1))
    ranges["SYO01"] = [(x, end if r == "script" else y, r, n) for x, y, r, n in ranges["SYO01"]]
    stray = extract.find_stray_text({"SYO01": {"d": d}}, jp, ranges)
    assert stray and all("SYO01" in s for s in stray)


def test_unknown_bytes_roundtrip_and_do_not_end_a_string():
    jp = jptext.Jp()
    raw = b"\x82\xa0\x01\x87\x90\x82\xa2\x00"  # あ, unknown byte, a duplicate cp932 code, い
    text, size = jp.decode(raw)
    assert size == len(raw) and text.endswith("い{end}") and "[01]" in text
    assert jp.encode(text) == raw


def test_digits_are_only_the_id_in_a_name_tag():
    # docs/re/text.md: bytes below 0x80 are a 2-digit pair the engine reads after ③ in 《》
    for e in spoken():
        rest = re.sub(r"\{nameon\}\{color\d\}\d\d", "", e["jp"])
        assert not re.search(r"[\x20-\x7e]", re.sub(r"\{[^}]*\}", "", rest)), e["id"]


def test_token_arguments_are_decimal():
    for e in spoken():
        for name, arg in re.findall(r"\{(expr|voice):([0-9A-F]+)\}", e["jp"]):
            raw = bytes.fromhex(arg)
            assert raw.isdigit() and len(raw) == {"expr": 2, "voice": 4}[name], e["id"]


def test_refs_name_their_string():
    for name, doc in docs().items():
        base = int(doc["base"], 16)
        for e in doc["entries"]:
            for r in e.get("refs", []):
                assert int(r["va"], 16) == base + int(e["off"], 16) + r["delta"], e["id"]
                assert r["delta"] == 0, f"{e['id']} is entered mid-string: split it"


def test_loader_entry_points_are_not_text_refs():
    # 4 sites pass the next overlay's entry point to the loader; it lands in this overlay's script
    sites = {("SYO02", 0x800D4598), ("SYO03", 0x800D92F4), ("SYO05", 0x800D0AD4), ("SYO06", 0x800D2C88)}
    for n, site in sites:
        doc = json.loads((SCRIPT / f"{n}.json").read_text(encoding="utf-8"))
        assert f"{site:#x}" not in {r["site"] for e in doc["entries"] for r in e.get("refs", [])}


def test_retired_lines_are_split_off_the_live_one():
    doc = json.loads((SCRIPT / "SYO02.json").read_text(encoding="utf-8"))
    by_off = {e["off"]: e for e in doc["entries"]}
    head, tail = by_off["0x17c90"], by_off["0x17c9c"]
    assert head["no_end"] and head["dead"] and head["jp"] == "欠番{nl2}欠番{nl2}"
    assert tail["refs"][0]["site"] == "0x800d194c" and tail["jp"].startswith("{clear}{nameon}")
    no_end = [e for e in entries() if e.get("no_end")]
    assert len(no_end) == 2 and all(e["dead"] for e in no_end)


def test_non_text_is_marked():
    for doc in docs().values():
        for e in doc["entries"]:
            assert "SYO0" not in e["jp"] and "ESCA" not in e["jp"], e["id"]  # loader paths
            assert ("form" in e) != ("data" in e), e["id"]
            if "data" in e:
                assert not extract.strip_tokens(e["jp"]), e["id"]  # control codes only
    # what a translator must leave alone says so
    forms = {e["form"] for e in spoken()}
    assert {"debug", "numbers", "dlg", "menu", "name", "fragment", "choice", "memcard", "battle"} <= forms
    names = [e for e in spoken() if e["form"] == "name"]
    assert len(names) == 49 and all(e["refs"][0]["kind"] == "word" for e in names)
    assert [e["id"] for e in spoken() if "{star}" in e["jp"] and e["form"] != "debug"] == ["syo01_219"]


def test_dead_means_nothing_points_at_it():
    dead = [e for e in entries() if e.get("dead")]
    assert len(dead) == 61 and not any(e.get("refs") for e in dead)


def test_rerun_refuses_to_wipe_translations(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"entries": [{"id": "a", "en": "hi"}]}), encoding="utf-8")
    assert extract.has_translation(p)
    p.write_text(json.dumps({"entries": [{"id": "a"}]}), encoding="utf-8")
    assert not extract.has_translation(p)
