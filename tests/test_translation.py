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


def test_fill_rows_wraps_to_the_box_and_breaks_pages_at_sentences():
    pages = fit.fill_rows("A short sentence ends here. " * 12, 2)
    assert len(pages[0]) <= 2 and all(len(p) <= 3 for p in pages)
    assert all(fit.width(r) <= fit.BODY_PX for p in pages for r in p)
    assert pages[0][-1].endswith(".")


def test_render_refuses_wrong_separators():
    jp = "{clear}{nameon}{color1}ひとみ{nameoff}{color2}{nl}「あ。{wait}{clear}{nl}い。{end}"
    e = {"jp": jp, "form": "dlg"}
    with pytest.raises(fit.FitError):
        fit.render(e, '"Ah. | One. | Two."', {"ひとみ": "Hitomi"})
    assert "Hitomi" in fit.render(e, '"Ah. | One."', {"ひとみ": "Hitomi"})
