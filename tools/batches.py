"""batches.py: translator batches. Every id's text ends up in script/*.json as `tl` (authored) and `en` (tokens).

    python -X utf8 tools/batches.py split [--size 120]   write work/tl/bNNN.tsv for what has no `tl` yet, never overwriting
    python -X utf8 tools/batches.py check bNNN           validate work/tl/bNNN.out.tsv; prints OK or one line per problem
    python -X utf8 tools/batches.py merge bNNN ...       check, then store it (and identical lines elsewhere); all batch files then follow
    python -X utf8 tools/batches.py status               translated lines per overlay

Input row: id, speaker, form, JP (` | ` page break, ` ^ ` voice on a new row, ` # ` choice option, ` / ` JP row break).
Output row: id, English, with the same ` | `, ` ^ ` and ` # ` structure.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fit  # noqa: E402

TL = ROOT / "work/tl"
SCRIPT = ROOT / "script"
FORMS = ("dlg", "narration", "choice")
AUTHOR_MARKS = re.compile(r"\s[|^#/]\s")
KANA_NAME = "ァ-ヶーぁ-ん"
# honorifics the ruling keeps, only after a name (貴様, お嬢さん and the like aren't honorifics)
HONORIFICS = [
    (re.compile(r"(?:[ァ-ヶー]|ひとみ)様"), "-sama"),
    (re.compile(r"(?:[ァ-ヶー]|ひとみ)さん"), "-san"),
    (re.compile(r"(?:[ァ-ヶー]|ひとみ)ちゃん"), "-chan"),
    (re.compile(r"(?:[ァ-ヶー]|ひとみ)(?<!ウズ)くん"), "-kun"),  # ウズく: to throb
    (re.compile(r"[ァ-ヶー]殿"), "-dono"),
    (re.compile(r"先輩"), "senpai"),
]


def docs():
    return {p: json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCRIPT.glob("*.json"))}


def save(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def translatable(e):
    return e.get("form") in FORMS and e.get("region") != "menu" and not (e.get("dead") and e.get("no_end"))


def is_raw(e):
    """Written by hand as a full token string: menus, fragments."""
    return not translatable(e)


def speaker(e):
    m, _b = fit.split_head(e["jp"])
    return m.group(4) or ""


def key(e):
    return speaker(e), e.get("form"), fit.compact_jp(e["jp"])


def rows_of(batch):
    rows = {}
    for ln in (TL / f"{batch}.out.tsv").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        eid, _, text = ln.partition("\t")
        if eid in rows:
            raise SystemExit(f"{batch}: {eid} twice")
        rows[eid] = text
    return rows


def load_glossary():
    """[(JP forms, EN forms, avoid forms)] from every table row of glossary.md."""
    out = []
    for ln in (ROOT / "glossary.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 7 or cells[1] in ("JP", "---"):
            continue
        jps = [j.strip() for j in re.split(r"[/,]", cells[1]) if j.strip()]
        ens = [re.sub(r"\(.*?\)", "", x).strip() for x in re.split(r"/", cells[2]) if x.strip()]
        avoid = [a.strip() for a in cells[5].split(",") if a.strip()]
        out.append((jps, ens, avoid, "exact" in cells[4]))
    return out


def whole_run(text, term):
    """term stands alone as a run of its script: ミン inside タイミング doesn't count."""
    cls = "ァ-ヶー" if re.match(r"[ァ-ヶー]", term) else ("一-龥" if re.match(r"[一-龥]", term) else "ぁ-ん")
    return re.search(rf"(?<![{cls}]){re.escape(term)}(?![{cls}])", text) is not None


def tokens_of(text):
    return sorted(t for t in re.findall(r"\{[^}]*\}", text) if t not in ("{nl}", "{nl2}"))


def control_problems(jp, en):
    """Control codes match the JP. Extra pages may add {wait} and {clear}, but never remove one."""
    pager = ("{wait}", "{clear}")
    a, b = tokens_of(jp), tokens_of(en)
    bad = []
    if [t for t in a if t not in pager] != [t for t in b if t not in pager]:
        bad.append(f"control codes differ: JP {a}, EN {b}")
    for t in pager:
        if b.count(t) < a.count(t):
            bad.append(f"fewer {t} than the JP")
    return bad


def problems(e, text, names, gloss):
    if is_raw(e):
        stripped = re.sub(r"\{[^}]*\}|　", "", text)
        bad = [] if stripped.isascii() else ["raw text not ASCII"]
        if tokens_of(text) != tokens_of(e["jp"]):
            bad.append(f"tokens differ from the JP: {tokens_of(e['jp'])}")
        return bad
    bad = []
    try:
        en = fit.render(e, text, names)
    except fit.FitError as err:
        return [str(err)]
    if not text.isascii() or "\t" in text or "{" in text or "}" in text:
        bad.append("not plain ASCII, or has a brace")
    if e.get("form") != "choice":
        bad += fit.lint(en)
    bad += control_problems(e["jp"], en)
    jp = re.sub(r"\{[^}]*\}", "", fit.split_head(e["jp"])[1])
    if e.get("form") != "choice":
        first = fit.parse_body(fit.split_head(e["jp"])[1])[1]
        if first:
            opened = first[0].lstrip("　").startswith("「")
            if opened and not (text.startswith('"') and text.rstrip().endswith('"')):
                bad.append('JP is speech: open and close with "')
            if not opened and text.startswith('"'):
                bad.append('JP has no quote mark (a thought or an aside): no opening "')
    for jps, ens, avoid, _x in gloss:
        for a in avoid:
            if re.search(rf"\b{re.escape(a)}\b", text):
                bad.append(f"avoid {a}")
        if any(whole_run(jp, j) for j in jps) and ens and not any(x.lower() in text.lower() for x in ens):
            bad.append(f"glossary: {jps[0]} needs {ens[0]}")
    for rx, form in HONORIFICS:
        if rx.search(jp) and form not in text.lower():
            bad.append(f"honorific {rx.pattern} needs {form}")
    return bad


def split(size):
    TL.mkdir(parents=True, exist_ok=True)
    seen, rows, dups = {}, [], []
    for path, doc in docs().items():
        for e in doc["entries"]:
            if not translatable(e):
                continue
            k = key(e)
            if k in seen:
                dups.append((e["id"], seen[k]))
                continue
            seen[k] = e["id"]
            if "tl" not in e:
                rows.append((path.stem, e))
    existing = [int(p.stem[1:]) for p in TL.glob("b[0-9][0-9][0-9].tsv") if p.stem != "b000"]  # b000: menus, by hand
    n = max(existing, default=0)
    if existing:
        raise SystemExit(f"{len(existing)} batch files exist in {TL}: not writing more")
    last, chars = None, 0
    out = None
    made = []
    for stem, e in rows:
        line = fit.compact_jp(e["jp"])
        if out is None or stem != last or len(out) >= size or chars >= 4200:
            n += 1
            out, chars = [], 0
            made.append((f"b{n:03}", out))
            last = stem
        out.append(f"{e['id']}\t{speaker(e)}\t{e['form']}{'/dead' if e.get('dead') else ''}\t{line}")
        chars += len(line)
    for name, lines in made:
        (TL / f"{name}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (TL / "dups.tsv").write_text("".join(f"{a}\t{b}\n" for a, b in dups), encoding="utf-8", newline="\n")
    print(f"{len(made)} batches, {len(rows)} lines, {len(dups)} identical lines follow their first copy")


def check(batch, quiet=False):
    ids = [ln.split("\t")[0] for ln in (TL / f"{batch}.tsv").read_text(encoding="utf-8").splitlines() if ln]
    rows = rows_of(batch)
    entries = {e["id"]: e for doc in docs().values() for e in doc["entries"]}
    names, gloss = fit.load_names(), load_glossary()
    bad = [f"{i}: missing" for i in ids if i not in rows] + [f"{i}: not in the batch" for i in rows if i not in ids]
    for i in ids:
        if i in rows:
            bad += [f"{i}: {p}" for p in problems(entries[i], rows[i], names, gloss)]
    for b in bad:
        print(b)
    if not bad and not quiet:
        print(f"{batch}: OK")
    return not bad


def merge(batches):
    for b in batches:
        if not check(b, quiet=True):
            raise SystemExit(f"{b} has problems: nothing merged")
    all_docs = docs()
    names = fit.load_names()
    dup_of = {}
    dup_file = TL / "dups.tsv"
    if dup_file.exists():
        for ln in dup_file.read_text(encoding="utf-8").splitlines():
            a, b = ln.split("\t")
            dup_of.setdefault(b, []).append(a)
    entries = {e["id"]: e for doc in all_docs.values() for e in doc["entries"]}
    count = 0
    for b in batches:
        for eid, text in rows_of(b).items():
            old = entries[eid].get("tl")
            # a copy reviewed apart from its first (はい: "Yes..." here, "All right..." there) stays as reviewed
            for i in [eid] + [d for d in dup_of.get(eid, []) if entries[d].get("tl") in (None, old)]:
                e = entries[i]
                e["tl"] = text
                e["en"] = fit.render(e, text, names)
                count += 1
    for e in entries.values():
        if e.get("form") == "name":
            e["en"] = names[e["jp"].replace("{end}", "")] + "{end}"
    for path, doc in all_docs.items():
        save(path, doc)
    sync_rows(entries)
    print(f"merged {count} entries")


def sync_rows(entries):
    """Every batch file follows the merged text, so re-checking or re-merging an older one can't bring an old draft back."""
    for p in sorted(TL.glob("*.out.tsv")):
        rows = rows_of(p.name.removesuffix(".out.tsv"))
        new = {i: entries[i].get("tl", t) for i, t in rows.items()}
        if new != rows:
            p.write_text("".join(f"{i}\t{t}\n" for i, t in new.items()), encoding="utf-8", newline="\n")


def status():
    total = done = 0
    for path, doc in docs().items():
        t = [e for e in doc["entries"] if translatable(e)]
        d = [e for e in t if "tl" in e]
        total += len(t)
        done += len(d)
        print(f"{path.stem}: {len(d)}/{len(t)}")
    print(f"total {done}/{total}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["split", "check", "merge", "status"])
    ap.add_argument("batches", nargs="*")
    ap.add_argument("--size", type=int, default=120)
    a = ap.parse_args()
    if a.cmd == "split":
        split(a.size)
    elif a.cmd == "check":
        sys.exit(0 if all([check(b) for b in a.batches]) else 1)
    elif a.cmd == "merge":
        merge(a.batches)
    else:
        status()
