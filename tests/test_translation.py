"""The merged script stays valid: authored text re-renders to what's stored, and every line fits its box."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import fit  # noqa: E402


def test_every_translated_line_passes_its_batch_check():
    names, gloss = fit.load_names(), batches.load_glossary()
    bad = []
    for doc in batches.docs().values():
        for e in doc["entries"]:
            if "tl" in e:
                bad += [f"{e['id']}: {p}" for p in batches.problems(e, e["tl"], names, gloss)]
                if batches.translatable(e) and fit.render(e, e["tl"], names) != e["en"]:
                    bad.append(f"{e['id']}: stored en is stale")
    assert not bad, "\n".join(bad[:20])


def test_name_table_fits_its_tag_and_follows_names_tsv():
    names, n = fit.load_names(), 0
    for doc in batches.docs().values():
        for e in doc["entries"]:
            if e.get("form") == "name":
                name = names[e["jp"].replace("{end}", "")]
                assert e["en"] == name + "{end}", e["id"]
                assert fit.width(name) <= fit.WINDOWS["name_tag"]["px"], e["id"]
                n += 1
    assert n == 49


def test_scene_menu_rows_fit_their_box_together():
    for path, doc in batches.docs().items():
        rows = sum(len(fit.raw_rows(e["en"])) for e in doc["entries"] if e.get("region") == "menu" and "en" in e and not e.get("dead"))
        assert rows <= fit.WINDOWS["scene_menu"]["rows"], path.stem


def test_partner_swap_prompt_fits_with_the_two_widest_partners():
    names = fit.load_names()
    wide = sorted(fit.width(names[n]) for n in fit.WINDOWS["partner_prompt"]["names"])[-2:]
    en = {e["id"]: e["en"] for e in batches.docs()[batches.SCRIPT / "common.json"]["entries"] if "en" in e}
    first = fit.raw_rows(en["common_099"])[0]
    assert sum(wide) + fit.width(fit.raw_rows(en["common_098"])[0]) + fit.width(first) + 2 <= fit.WINDOWS["partner_prompt"]["px"]


def test_raw_rows_are_measured_against_their_box():
    long = "{mark2}　" + "End Partnership " * 2 + "{nl2}{end}"
    assert fit.raw_box({"id": "common_002", "form": "menu"}) == "partner_menu"
    assert fit.raw_lint({"id": "common_002", "form": "menu"}, long)  # over 140 px
    assert not fit.raw_lint({"id": "common_012", "form": "menu"}, long)  # the card menu holds 224
    assert fit.raw_lint({"id": "common_012", "form": "menu"}, "a{nl}" * 7 + "{end}")  # over 6 rows
    assert fit.raw_lint({"id": "common_097", "form": "fragment"}, "x{end}", 224)  # follows the name
    assert fit.width("　a") == fit.INDENT_PX + fit.width("a") and fit.width("　") == fit.INDENT_PX


def test_raw_blanks_match_the_jp():
    e = {"id": "common_012", "form": "menu", "jp": "　{mark1}あ{nl2}{end}"}
    assert not batches.problems(e, "　{mark1}a{nl2}{end}", {"x": "x"}, [])
    assert any("blanks" in p for p in batches.problems(e, "{mark1}a{nl2}{end}", {"x": "x"}, []))


def test_fill_rows_wraps_to_the_box_and_breaks_pages_at_sentences():
    pages = fit.fill_rows("A short sentence ends here. " * 12, 2)
    assert len(pages[0]) <= 2 and all(len(p) <= 3 for p in pages)
    assert all(fit.width(r) <= fit.BODY_PX for p in pages for r in p)
    assert pages[0][-1].endswith(".")


def test_fill_rows_leaves_no_stub_last_row():
    pages = fit.fill_rows("The day a dragon tore off this arm, I died.", 2)
    assert len(pages) == 1 and len(pages[0]) == 2 and pages[0][1] == "I died."


def test_added_page_with_a_scrap_is_refused():
    e = {"jp": "{clear}{nameon}{color1}ひとみ{nameoff}{color2}{nl}「あ。{end}", "form": "dlg"}
    with pytest.raises(fit.FitError):
        fit.render(e, '"I\'m the man who used the fortune-enhanced soldiers to try to take you."', {"ひとみ": "Hitomi"})


def test_merge_keeps_a_reviewed_copy_and_every_batch_file_follows(tmp_path, monkeypatch):
    jp = "{clear}{nameon}{color1}ひとみ{nameoff}{color2}{nl}「はい…。{end}"
    entries = [{"id": i, "jp": jp, "form": "dlg", "en": "", "tl": t} for i, t in (("a", '"All right..."'), ("b", '"Yes..."'))]
    script, tl = tmp_path / "script", tmp_path / "tl"
    script.mkdir(), tl.mkdir()
    batches.save(script / "x.json", {"entries": entries})
    (tl / "dups.tsv").write_text("b\ta\n", encoding="utf-8")
    for name, rows in (("b1", 'a\t"All right..."\n'), ("r1", 'a\t"Okay..."\n')):
        (tl / f"{name}.tsv").write_text("a\n", encoding="utf-8")
        (tl / f"{name}.out.tsv").write_text(rows, encoding="utf-8")
    monkeypatch.setattr(batches, "SCRIPT", script)
    monkeypatch.setattr(batches, "TL", tl)
    monkeypatch.setattr(fit, "load_names", lambda: {"ひとみ": "Hitomi"})
    monkeypatch.setattr(batches, "load_glossary", lambda: [])
    batches.merge(["r1"])
    stored = {e["id"]: e["tl"] for e in batches.docs()[script / "x.json"]["entries"]}
    assert stored == {"a": '"Okay..."', "b": '"Yes..."'}
    assert batches.rows_of("b1") == {"a": '"Okay..."'}


def test_render_refuses_wrong_separators():
    jp = "{clear}{nameon}{color1}ひとみ{nameoff}{color2}{nl}「あ。{wait}{clear}{nl}い。{end}"
    e = {"jp": jp, "form": "dlg"}
    with pytest.raises(fit.FitError):
        fit.render(e, '"Ah. | One. | Two."', {"ひとみ": "Hitomi"})
    assert "Hitomi" in fit.render(e, '"Ah. | One."', {"ひとみ": "Hitomi"})
