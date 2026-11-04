"""extract.py: decode every script string into script/*.json, with its references and metadata.

    python -X utf8 tools/extract.py [--verbose] [--out DIR]   write script/ (or DIR)
    python -X utf8 tools/extract.py --check                   verify only, write nothing

Reads `tbl/text_ranges.tsv` (file, start, end, region) and `tbl/jp.tbl`, walks each declared
range with tools/jptext.py, and writes one JSON per program with text, plus `script/common.json`
for the block that is byte-identical in all eight overlays (partner menu, SAVE/LOAD, memory-card
messages, character name table) so it is translated once and written eight times. A `*` row
in the ranges file is a shared span: it is walked in every overlay and the copies must match.

--check (what tests/test_extract.py calls) fails on:
  - a byte in a text range that no entry covers and that is not 00 padding;
  - text outside every declared range (an extraction miss), found two ways: a raw scan, and
    every lui/addiu or word pointer whose target decodes as Japanese (catches short strings);
  - a string split by a range boundary;
  - the eight copies of a shared span differing;
  - a token in the text that tbl/jp.tbl does not name;
  - a `block` span that is mostly record bytes (a mis-declared range).

An entry is a string, not a translation: id, file offset, byte size, decoded text (tokens and
all), speaker, form, and the references that must follow it if it moves. `dead` = nothing in the
game points at it (`docs/re/text.md`). `no_end` = the bytes run on into the next entry.
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import jptext  # noqa: E402
import mips  # noqa: E402

TREE = ROOT / "work/tree"
BASE = 0x800C1C28
SCRIPTS = [f"SYO{i:02d}" for i in range(8)]
# other program files: tree path, file offset 0's address (docs/re/disc.md). STAFF's is a guess.
OTHERS = {"BATTLE": ("ESCA/PRG/BATTLE.BIN", 0x801D8000), "TITLE": ("ESCA/PRG/TITLE.BIN", 0x801D8000),
          "MOVIE": ("ESCA/PRG/MOVIE.BIN", 0x801D8000), "STAFF": ("ESCA/PRG/STAFF.BIN", 0x801D8000),
          "SLPS_010": ("SLPS_010.15", 0x8000F800)}
JAL_LOADER = 0x0C00DE41  # jal 0x80037904, the overlay loader: a0 = path, a1 = entry point
NOT_SPOKEN = ("numbers", "debug", "memcard", "battle")  # regions whose form is the region itself
# characters that make a string text even with no kana/kanji: punctuation and fullwidth forms
PUNCT = set("、。，．！？…―—ー「」『』（）〈〉《》【】〔〕・：；～♪☆★○●△▲▽▼□■※→←↑↓　")


def tree_path(name):
    return OTHERS[name][0] if name in OTHERS else f"ESCA/PRG/{name}.BIN"


def base_of(name):
    return OTHERS[name][1] if name in OTHERS else BASE


def strip_tokens(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == "{":
            j = text.find("}", i)
            if j < 0:
                raise ValueError("unclosed token")
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def tokens(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == "{":
            j = text.find("}", i)
            out.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def classify(text):
    """text | ascii | control. Raises on an undecodable byte, i.e. a misparse."""
    body = strip_tokens(text)
    if "[" in body:
        raise ValueError("undecodable byte")
    if any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff"
           or "\uff01" <= c <= "\uff5e" or c in PUNCT for c in body):
        return "text"
    if body and all(" " <= c < "\x7f" for c in body):
        return "ascii"
    return "control"


def speaker_of(text):
    """Name inside the name tag {nameon}...{nameoff}, minus colour tokens and id digits."""
    a = text.find("{nameon}")
    b = text.find("{nameoff}", a + 8) if a >= 0 else -1
    if b < 0:
        return None
    inner, out, i = text[a + 8:b], [], 0
    while i < len(inner):
        if inner[i] == "{":
            i = inner.find("}", i) + 1
        elif inner[i].isdigit():
            i += 1
        else:
            out.append(inner[i])
            i += 1
    return "".join(out) or None


def form_of(text, region):
    if region in NOT_SPOKEN:
        return region
    marks = any(t.startswith("mark") for t in tokens(text))
    if region == "names":
        return "name"
    if region == "prompt":
        return "fragment"  # a piece the code joins to a name (`Xをパートナーにしますか？`)
    if region == "common":
        return "menu"
    if marks:
        return "choice"
    if "{nameon}" in text:
        return "dlg"
    return "narration"


def load_ranges(path=None):
    """{file: [(start, end, region, note)]}, in file order. A `*` file means every overlay."""
    ranges = {}
    for line in Path(path or ROOT / "tbl/text_ranges.tsv").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f, a, b, region, note = (line.split("\t") + [""])[:5]
        files = SCRIPTS if f == "*" else [Path(f).stem]
        for name in files:
            ranges.setdefault(name, []).append((int(a, 16), int(b, 16), region, note))
    for name in ranges:
        ranges[name].sort()
    return ranges


def walk(d, jp, a, b):
    """Entries covering [a, b): (off, size, text, kind). Raises on a byte that is neither."""
    out, pos = [], a
    while pos < b:
        if d[pos] == 0:
            pos += 1
            continue
        text, size = jp.decode(d, pos, maxlen=b - pos + 1)
        if pos + size > b:
            raise ValueError(f"string at {pos:#x} runs past the range end {b:#x}")
        out.append((pos, size, text, classify(text)))
        pos += size
    return out


def walk_block(d, jp, a, b):
    """Entries in a `block` region, plus how many record bytes were skipped.

    A block interleaves strings with records the engine reads as data. Every byte that does
    not start a whole text string is record data; the caller fails the span if that is most
    of it, which is what a range declared over code would look like.
    """
    out, pos, skipped = [], a, 0
    while pos < b:
        if d[pos] != 0:
            try:
                text, size = jp.decode(d, pos, maxlen=b - pos + 1)
                kind = classify(text)
            except ValueError:
                text = None
            if text is not None and pos + size <= b and kind == "text":
                out.append((pos, size, text, kind))
                pos += size
                continue
        pos += 1
        skipped += 1
    return out, skipped


def passes_entry_to_loader(d, o):
    """`addiu $a1,..` right before `jal loader`: a1 is the next overlay's code entry point, an
    address that can land in this overlay's text by chance (4 did). Not a reference to text."""
    if o + 8 > len(d):
        return False
    low, nxt = struct.unpack_from("<2I", d, o)
    return (low >> 16) & 31 == 5 and nxt == JAL_LOADER


def refs_for(d, spans, base=BASE):
    """(kind, site_va, target_va) for every read of a byte inside one of `spans`."""
    out = []
    for va, target, _op in mips.lui_pairs(d, base):
        off = target - base
        if any(a <= off < b for a, b in spans) and not passes_entry_to_loader(d, va - base):
            out.append(("code", va, target))
    for o in range(0, len(d) - 3, 4):
        v = struct.unpack_from("<I", d, o)[0]
        off = v - base
        if any(a <= off < b for a, b in spans) and not any(a <= o < b for a, b in spans):
            out.append(("word", base + o, v))
    return out


def attach(refs, entries, data=(), blocks=(), base=BASE):
    """Map entry offset -> [{kind, site, va, delta}]; refs into a data span are kept there.

    A ref into the record bytes of a `block` span is returned separately: those records are
    engine data, not moved text, so the ref needs no rewrite.
    """
    out = {o: [] for o, _s, _t, _k in entries}
    out.update({o: [] for o, _s, _n in data})
    loose = []
    for kind, site, target in refs:
        for o, s, _t, _k in entries:
            if base + o <= target < base + o + s:
                out[o].append({"kind": kind, "site": f"{site:#x}", "va": f"{target:#x}",
                               "delta": target - (base + o)})
                break
        else:
            for o, s, _n in data:
                if base + o <= target < base + o + s:
                    out[o].append({"kind": kind, "site": f"{site:#x}", "va": f"{target:#x}",
                                   "delta": target - (base + o)})
                    break
            else:
                if any(base + a <= target < base + b for a, b in blocks):
                    loose.append((kind, site, target))
                    continue
                raise ValueError(f"{kind} ref {site:#x} -> {target:#x} hits no entry or data span")
    return out, loose


def split_at_mid_refs(d, jp, entries, refs):
    """A ref into the middle of a string makes the rest its own entry, so the rest can move.

    The head (`欠番↓`, retired lines left in front of the live one) runs on into the tail and
    nothing points at it. A head something does point at would need the tail to stay glued to
    it, which nothing here handles, so that is an error.
    """
    out = []
    for e in entries:
        o, s, t, k, region = e
        cuts = sorted({r["delta"] for r in refs[o] if r["delta"]})
        if not cuts:
            out.append(e)
            continue
        if len(cuts) > 1 or any(not r["delta"] for r in refs[o]):
            raise ValueError(f"string at {o:#x} is entered at {cuts} and at its start")
        c = cuts[0]
        head = jp.decode(bytes(d[o:o + c]) + b"\0")[0].removesuffix("{end}")
        tail, tail_size = jp.decode(d, o + c)  # a cut inside a token or character breaks here
        if jp.encode(head) != d[o:o + c] or tail_size != s - c:
            raise ValueError(f"ref into {o:#x}+{c:#x} lands inside a token or character")
        out += [(o, c, head, "text", region), (o + c, s - c, tail, "text", region)]
        refs[o + c] = [dict(r, delta=0) for r in refs[o]]
        refs[o] = []
    return out


def scan_file(name, jp, ranges):
    """(entries [(off,size,text,kind,region)], data [(off,size,note)], refs, problems)."""
    d = (TREE / tree_path(name)).read_bytes()
    base = base_of(name)
    rs = ranges.get(name, [])
    entries, data, blocks, problems = [], [], [], []
    for a, b, region, note in rs:
        mode, _, tag = region.partition("+")
        if mode == "data":
            if not note:
                problems.append(f"{name}: data span {a:#x}-{b:#x} has no note")
            data.append((a, b - a, note))
            continue
        if mode == "block":
            es, skipped = walk_block(d, jp, a, b)
            if not es:
                problems.append(f"{name} {tag} {a:#x}-{b:#x}: no text string found")
            elif skipped * 4 > (b - a) * 3:
                problems.append(f"{name} {tag} {a:#x}-{b:#x}: {skipped} of {b - a} bytes "
                                f"are record data; wrong span?")
            blocks.append((a, b))
            entries += [(o, s, t, k, tag) for o, s, t, k in es]
            continue
        es = walk(d, jp, a, b)
        covered = bytearray(b - a)
        for o, s, _t, _k in es:
            covered[o - a:o - a + s] = b"\x01" * s
        bad = [i + a for i, c in enumerate(covered) if not c and d[i + a] != 0]
        if bad:
            problems.append(f"{name} {region} {a:#x}-{b:#x}: {len(bad)} uncovered non-zero "
                            f"bytes, first {bad[0]:#x} byte {d[bad[0]]:#04x}")
        entries += [(o, s, t, k, tag or region) for o, s, t, k in es]
    four = [(o, s, t, k) for o, s, t, k, _r in entries]
    refs, loose = attach(refs_for(d, [(a, b) for a, b, _r, _n in rs], base), four, data, blocks, base)
    entries = split_at_mid_refs(d, jp, entries, refs)
    return {"d": d, "entries": entries, "data": data, "refs": refs, "loose": loose,
            "problems": problems}


def find_stray_targets(files, jp, ranges):
    """Pointer targets outside every range that decode as Japanese, however short.

    The raw scan below needs 3 characters to stay above code noise; a real `はい` has a
    pointer, so this catches what it can't. Noise that looks like text gets a `data` row.
    """
    out = []
    for name, info in files.items():
        d, base = info["d"], base_of(name)
        declared = [(a, b) for a, b, _r, _n in ranges.get(name, [])]
        n = len(d) // 4
        targets = {t for _va, t, _op in mips.lui_pairs(d, base)}
        targets.update(struct.unpack("<%dI" % n, d[:n * 4]))
        for t in sorted(targets):
            o = t - base
            if not 0 <= o < len(d) or any(a <= o < b for a, b in declared):
                continue
            try:
                text, _size = jp.decode(d, o, maxlen=400)
            except ValueError:
                continue
            body = strip_tokens(text)
            if "[" not in body and any(is_jp(c) for c in body):
                out.append(f"{name}: pointer target outside every range at {o:#x}: {text[:60]}")
    return out


def is_jp(c):
    return "぀" <= c <= "ヿ" or "一" <= c <= "鿿" or "！" <= c <= "～"


def find_stray_text(files, jp, ranges):
    """Text-looking strings outside every declared range: an extractor blind spot."""
    out = []
    # a string classify() accepts holds only these bytes, so only runs of them need decoding
    runs = re.compile(rb"[\x0a\x20-\x7e\x80-\xfc]{6,}\x00")
    for name, info in files.items():
        d = info["d"]
        declared = [(a, b) for a, b, _r, _n in ranges.get(name, [])]
        for m in runs.finditer(d):
            pos = m.start()
            while pos < m.end() - 1:
                if any(a <= pos < b for a, b in declared):
                    pos += 1
                    continue
                try:
                    text, size = jp.decode(d, pos, maxlen=1024)  # longest real string is under 400
                    if classify(text) != "text":
                        pos += 1
                        continue
                except ValueError:
                    pos += 1
                    continue
                body = strip_tokens(text)
                # kanji-only runs like 劔劔劔 are pixels or code; real kanji-only text has a pointer
                if sum(1 for c in body if is_jp(c)) >= 3 and any(not "一" <= c <= "鿿" and is_jp(c)
                                                                 for c in body):
                    out.append(f"{name}: text outside every range at {pos:#x} ({size} bytes): "
                               f"{text[:60]}")
                pos += max(size, 1)
    return out


def entry_json(eid, region, o, s, t, k, refs):
    e = {"id": eid, "region": region, "off": f"{o:#x}", "size": s, "jp": t}
    if k == "text":
        e["form"] = form_of(t, region)
        sp = speaker_of(t)
        if sp:
            e["speaker"] = sp
    else:
        e["data"] = k
    if not t.endswith("{end}"):
        e["no_end"] = True
    if refs:
        e["refs"] = refs
    elif k == "text" and region != "memcard":  # the title is read through its header at 0x6FC80
        e["dead"] = True
    return e


def has_translation(path):
    return path.is_file() and any("en" in e for e in
                                  json.loads(path.read_text(encoding="utf-8"))["entries"])


def main():
    verbose = "--verbose" in sys.argv
    check_only = "--check" in sys.argv
    out = ROOT / "script"
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    jp = jptext.Jp()
    ranges = load_ranges()
    if not ranges:
        raise SystemExit("tbl/text_ranges.tsv has no ranges")
    programs = SCRIPTS + list(OTHERS)
    files = {n: scan_file(n, jp, ranges) for n in programs}
    problems = [p for n in programs for p in files[n]["problems"]]
    problems += find_stray_text(files, jp, ranges)
    problems += find_stray_targets(files, jp, ranges)
    common_spans = [(a, b) for a, b, r, _n in ranges["SYO00"] if r in ("common", "names", "prompt")]
    if not common_spans:
        raise SystemExit("tbl/text_ranges.tsv declares no common range")
    for ca, cb in common_spans:
        first = files["SYO00"]["d"][ca:cb]
        for n in SCRIPTS:
            if files[n]["d"][ca:cb] != first:
                problems.append(f"common block {ca:#x}-{cb:#x} differs in {n}.BIN")
    known = set(jp.t.ctrl_enc)
    used = {t.partition(":")[0] for n in programs for e in files[n]["entries"]
            for t in tokens(e[2])}
    if used - known:
        problems.append(f"tokens not in tbl/jp.tbl: {sorted(used - known)}")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        return 1
    if verbose:
        print(f"tokens used: {', '.join(sorted(used))}")
        for n in programs:
            es = files[n]["entries"]
            print(f"{n}: {len(es)} entries ({sum(1 for e in es if e[3] == 'text')} text), "
                  f"{sum(len(e[2]) for e in es)} chars, "
                  f"{sum(len(files[n]['refs'][e[0]]) for e in es)} refs, "
                  f"{len(files[n]['data'])} data spans, {len(files[n]['loose'])} block refs")
    if check_only:
        print("OK: ranges covered, no text outside them, shared block identical")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    kept = [p.name for p in sorted(out.glob("*.json")) if has_translation(p)]
    if kept:  # a rerun rebuilds entries from the disc and would wipe the English
        raise SystemExit(f"{out} already holds translations ({', '.join(kept)}); use --out")

    def in_common(o):
        return any(ca <= o < cb for ca, cb in common_spans)

    ces = [e for e in files["SYO00"]["entries"] if in_common(e[0])]
    common = []
    for n, (o, s, t, k, region) in enumerate(ces, 1):
        rl = [dict(r, file=f"{f}.BIN") for f in SCRIPTS for r in files[f]["refs"][o]]
        common.append(entry_json(f"common_{n:03d}", region, o, s, t, k, rl))
    (out / "common.json").write_text(json.dumps(
        {"file": "ESCA/PRG/SYO00-07.BIN", "base": f"{BASE:#x}",
         "note": "shared block, identical in all 8 overlays, spans "
                 + ", ".join(f"{ca:#x}-{cb:#x}" for ca, cb in common_spans),
         "entries": common}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    total = 0
    for name in programs:
        es, n = [], 0
        for o, s, t, k, region in files[name]["entries"]:
            if name in SCRIPTS and in_common(o):
                continue
            n += 1
            total += 1
            es.append(entry_json(f"{name.lower()}_{n:03d}", region, o, s, t, k,
                                 files[name]["refs"][o]))
        if not es:
            continue
        doc = {"file": tree_path(name), "base": f"{base_of(name):#x}", "entries": es}
        if files[name]["data"]:
            doc["data"] = [{"off": f"{o:#x}", "size": s, "why": note,
                            **({"refs": files[name]["refs"][o]} if files[name]["refs"][o] else {})}
                           for o, s, note in files[name]["data"]]
        (out / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8", newline="\n")
    print(f"wrote {out}: common.json ({len(common)}) + program files ({total} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
