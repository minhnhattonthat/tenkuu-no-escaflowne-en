"""pairs.py: one review file per chapter, in script order, for the reviewer and story passes.

    python -X utf8 tools/pairs.py [OUTDIR]   default work/qa/story/chapters; one `>> id | speaker | JP` / EN pair per entry
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import fit  # noqa: E402


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work/qa/story/chapters"
    out.mkdir(parents=True, exist_ok=True)
    for path, doc in batches.docs().items():
        lines = []
        for e in doc["entries"]:
            if "tl" not in e:
                continue
            if batches.translatable(e):
                lines += [f">> {e['id']} | {batches.speaker(e)} | {fit.compact_jp(e['jp'])}", e["tl"]]
            else:
                lines += [f">> {e['id']} | | {e['jp']}", e["tl"]]
        (out / f"{path.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(path.stem, len(lines) // 2)


if __name__ == "__main__":
    main()
