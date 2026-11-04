"""fit.py: authored English -> the game's token string, wrapped to the measured boxes (data/windows.json).

Authored text (`tl` in script/*.json):
    dlg, narration, bark:  `page | page ^ page`. `|` stands for each JP page break, `^` for a voice clip that starts on a
                           new row without a page break; both are matched against the JP. ` / ` forces a new row.
    choice:                `prompt # option # option`.
    menu, fragment:        the full token string, by hand.

A text that outgrows its page runs on to an extra page, at a sentence end if the page has one. The engine ignores a
newline at column 0 (0x8003B10C), so `{clear}{nl2}` starts on row 0: a page holds 3 rows, or 2 under a name tag.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402

WINDOWS = json.loads((ROOT / "data/windows.json").read_text(encoding="utf-8"))
BODY_PX = WINDOWS["dialogue"]["px_body"]
CHOICE_PX = WINDOWS["choice"]["px"]
CHOICE_ROWS = WINDOWS["choice"]["rows"]
INDENT_PX = font.FULLWIDTH_PX
STUB_CHARS = 6  # a last row shorter than this is one orphaned word
STUB_PAGE_WORDS = 3  # an extra page must carry more than this, or it costs a button press for a scrap
NEXT_PAGE = "{wait}{clear}{nl}"
RUN = re.compile(r"((?:\{[^}]*\})+)")
TOKEN = re.compile(r"\{[^}]*\}")
HEAD = re.compile(r"^　?(\{clear\})?(?:\{nameon\}(\{color\d\})(\d\d)?([^{]*)((?:\{expr:\d+\})?)\{nameoff\}(\{color\d\})(?:\{nl2?\})+)?")
SPLIT = re.compile(r"\s+([|^])\s+")
SENTENCE_END = re.compile(r"(\.|!|\?)[\"')]*$")
FULLWIDTH_DIGIT = {c: str(i) for i, c in enumerate("０１２３４５６７８９")}
_font = None


class FitError(ValueError):
    pass


def width(text):
    global _font
    _font = _font or font.Font()
    return _font.width(text)


def load_names(path=ROOT / "tbl/names.tsv"):
    rows = [ln.split("\t") for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    return {r[0]: r[1] for r in rows}


def is_blank(text):
    return not text.strip(" 　")


def is_newline(tok):
    return tok in ("{nl}", "{nl2}")


def split_head(jp):
    m = HEAD.match(jp)
    return m, jp[m.end():]


def make_head(m, names):
    """The name tag with its portrait digits and expression id, the name in English."""
    head = m.group(1) or ""
    if m.group(4) is not None:
        name = m.group(4)
        if name not in names:
            raise FitError(f"name not in tbl/names.tsv: {name}")
        head += f"{{nameon}}{m.group(2)}{m.group(3) or ''}{names[name]}{m.group(5)}{{nameoff}}{m.group(6)}{{nl}}"
    return head, m.group(4) is not None


def parse_body(body):
    """(lead tokens, [JP text], [(kind, tokens)], tail tokens). kind: '|' page break, '^' voice on a new row."""
    parts = RUN.split(body)
    texts, seps, lead, pending = [], [], [], None
    # parts: text, run, text, run, ...; blank text counts as nothing, so its neighbours' runs join
    for i, part in enumerate(parts):
        if i % 2:
            toks = TOKEN.findall(part)
            pending = (pending or []) + toks
        elif not is_blank(part):
            if not texts:
                lead = [t for t in (pending or []) if not is_newline(t)]
            elif all(is_newline(t) for t in pending):
                texts[-1] += " / " + part
                pending = None
                continue
            else:
                toks = list(pending)
                while toks and is_newline(toks[0]):
                    toks.pop(0)
                hard = any(t in ("{wait}", "{pageend}", "{clear}", "{star}") for t in toks)
                seps.append(("|" if hard else "^", toks))
            texts.append(part)
            pending = None
    tail = list(pending or [])
    while tail and is_newline(tail[0]):
        tail.pop(0)
    return lead, texts, seps, tail


def compact_jp(jp):
    """One-line JP for a batch file: page breaks and voice starts as the author must write them."""
    _m, body = split_head(jp)
    if "{mark" in body:
        prompt, opts = parse_choice(body)
        return " # ".join([prompt] + [o for _i, _mk, _d, o in opts])
    _lead, texts, seps, _tail = parse_body(body)
    out = texts[0].strip("　") if texts else ""
    for (kind, _t), text in zip(seps, texts[1:]):
        out += f" {kind} " + text.strip("　")
    return out.replace(" / 　", " / ")


def tl_shape(jp):
    """The separators an authored text must have, in order."""
    _m, body = split_head(jp)
    return [k for k, _t in parse_body(body)[2]]


def fill_rows(text, first_rows):
    """[[row, row], [row...]]: the text wrapped to pages, the first page holding first_rows rows, each later one 3."""
    pages, rows, cur = [], [], ""
    limit = first_rows

    def flush_page():
        nonlocal rows, limit
        pages.append(rows)
        rows, limit = [], 3

    chunks = [c.split() for c in text.split(" / ")]
    words = []
    for n, chunk in enumerate(chunks):
        if n:
            words.append(None)  # a forced row break
        words += chunk
    i = 0
    while i < len(words):
        w = words[i]
        if w is None:
            rows.append(cur)
            cur = ""
            if len(rows) == limit:
                flush_page()
            i += 1
            continue
        if width(w) > BODY_PX:
            raise FitError(f"word too wide: {w}")
        trial = f"{cur} {w}" if cur else w
        if width(trial) <= BODY_PX:
            cur = trial
            i += 1
            continue
        rows.append(cur)
        cur = ""
        if len(rows) == limit:
            # page full: back up to the last sentence end, if that leaves the page at least half used
            flat = " ".join(rows).split()
            for j in range(len(flat) - 1, max(len(flat) // 2 - 1, 0), -1):
                if SENTENCE_END.search(flat[j]):
                    undo = len(flat) - 1 - j
                    k = i
                    while undo:
                        k -= 1
                        if words[k] is not None:
                            undo -= 1
                    i = k
                    kept, row = [], ""
                    for x in flat[:j + 1]:
                        t = f"{row} {x}" if row else x
                        if width(t) <= BODY_PX:
                            row = t
                        else:
                            kept.append(row)
                            row = x
                    kept.append(row)
                    rows = kept
                    break
            flush_page()
    if cur:
        rows.append(cur)
    if rows:
        pages.append(rows)
    if len(chunks) == 1:  # shortcut: a text with forced ` / ` rows keeps its stubs, none has one on a multi-row page
        for page in pages:
            unstub(page)
    return pages


def unstub(rows):
    """Pull a word down so a page's last row isn't one orphaned word. Never changes the row count."""
    while can_pull(rows) and (len(rows[-1]) < STUB_CHARS or " " not in rows[-1]):
        rows[-2], word = rows[-2].rsplit(" ", 1)
        rows[-1] = f"{word} {rows[-1]}"


def can_pull(rows):
    return len(rows) > 1 and " " in rows[-2] and width(f"{rows[-2].rsplit(' ', 1)[1]} {rows[-1]}") <= BODY_PX


def render_dialogue(jp, tl, names):
    m, body = split_head(jp)
    head, named = make_head(m, names)
    lead, texts, seps, tail = parse_body(body)
    if not texts:
        return head + "".join(lead) + "".join(tail)
    parts = SPLIT.split(tl.strip())
    segs, kinds = parts[0::2], parts[1::2]
    if kinds != [k for k, _t in seps]:
        raise FitError(f"separators {kinds} but the JP has {[k for k, _t in seps]}")
    out = [head, "".join(lead)]
    left = 2 if named else 3

    def place(seg):
        nonlocal left
        pages = fill_rows(seg, left)
        for n, rows in enumerate(pages):
            if n:
                if len(" ".join(rows).split()) <= STUB_PAGE_WORDS:
                    raise FitError(f"added page holds a scrap, reword: {rows}")
                out.append(NEXT_PAGE)
                left = 3
            out.append("{nl}".join(rows))
            left -= len(rows)

    place(segs[0])
    for seg, (kind, toks) in zip(segs[1:], seps):
        if kind == "^":
            if left:
                out.append("{nl}")
            else:
                out.append(NEXT_PAGE)
                left = 3
            out.append("".join(toks))
        else:
            out.append("".join("{nl}" if is_newline(t) else t for t in toks))
            if "{clear}" in toks:
                left = 3
            elif not left:
                raise FitError("text continues below a full page without a clear")
        place(seg)
    return "".join(out) + "".join(tail)


def parse_choice(body):
    """(JP prompt, [(indent, mark token, digit, JP text)])."""
    pre = body[:body.index("{mark")].rstrip("　")
    prompt = " ".join(t for t in re.split(r"\{[^}]*\}", pre) if not is_blank(t))
    opts = []
    for m in re.finditer(r"(　*)(\{mark\d+\})\{color4\}(.)）\{color2\}　?([^{]*(?:\{nl2?\}　+[^{　][^{]*)?)", body):
        text = re.sub(r"\{nl2?\}　*", " / ", m.group(4))
        opts.append((m.group(1), m.group(2), FULLWIDTH_DIGIT[m.group(3)], text))
    return prompt, opts


def render_choice(jp, tl, names):
    m, body = split_head(jp)
    head, _named = make_head(m, names)
    _prompt, opts = parse_choice(body)
    parts = [p.strip() for p in tl.split(" # ")]
    if len(parts) != len(opts) + 1:
        raise FitError(f"{len(parts) - 1} options but the JP has {len(opts)}")
    tail = re.search(r"((?:\{[^}]*\}|　)*)$", body).group(1).replace("　", "")
    tail_toks = TOKEN.findall(tail)
    while tail_toks and is_newline(tail_toks[0]):
        tail_toks.pop(0)
    prompt = parts[0]
    if width(prompt) > CHOICE_PX:
        raise FitError(f"prompt too wide: {prompt}")
    rows = [prompt]
    for (indent, mark, digit, _jp), text in zip(opts, parts[1:]):
        lead_px = INDENT_PX * len(indent)
        label = f"{digit}) "
        words, cur, first = text.split(), label, True
        built = []
        hang = "　" * (len(indent) + 1)
        room = CHOICE_PX - lead_px
        for w in words:
            trial = f"{cur}{w}" if cur.endswith(" ") else f"{cur} {w}"
            if width(trial) > room:
                built.append(cur.rstrip())
                cur, room, first = w, CHOICE_PX - INDENT_PX * len(hang), False
            else:
                cur = trial
        built.append(cur)
        rows.append(f"{indent}{mark}{{color4}}{label.strip()}{{color2}} " + built[0][len(label):])
        rows += [hang + r for r in built[1:]]
    if len(rows) + 1 > CHOICE_ROWS:
        raise FitError(f"{len(rows) + 1} rows, the box holds {CHOICE_ROWS}")
    return head + "{nl}".join(rows) + "".join(tail_toks)


def render(e, tl, names):
    """The token string for an entry's authored text."""
    form = e.get("form")
    if form == "choice" and "{nameon}" in e["jp"]:
        return render_choice(e["jp"], tl, names)
    if form in ("dlg", "narration"):
        return render_dialogue(e["jp"], tl, names)
    return tl  # menu, fragment, battle: by hand


def pages_of(en):
    """[[row text]] as the player sees it: name tag dropped, tokens gone. For lint and review."""
    m = re.search(r"\{nameoff\}\{color\d\}\{nl\}", en)
    named = bool(m)
    body = en[m.end():] if m else en
    pages = re.split(r"\{clear\}", body)
    out = []
    for n, page in enumerate(pages):
        rows = [TOKEN.sub("", r) for r in re.split(r"\{nl2?\}", page)]
        rows = [r for r in rows if r]
        if rows:
            out.append((named and n == 0, rows))
    return out


def lint(en):
    """Problems in a dialogue token string, read from the string itself rather than from how it was built."""
    bad = []
    for named, rows in pages_of(en):
        if len(rows) > (2 if named else 3):
            bad.append(f"{len(rows)} rows on a page: {rows}")
        for r in rows:
            if width(r) > BODY_PX:
                bad.append(f"{width(r)} px: {r}")
        if len(rows) > 1 and len(rows[-1]) < STUB_CHARS:
            bad.append(f"stub last row: {rows}")
        elif can_pull(rows) and " " not in rows[-1] and not re.search(r"\{voice:\w+\}" + re.escape(rows[-1]), en):
            bad.append(f"one-word last row: {rows}")  # a row that opens its own voice clip can't take a word from above
    return bad


def raw_box(e):
    """The data/windows.json key a hand-written entry draws in."""
    if e.get("form") == "fragment":
        return "partner_prompt"
    if e.get("region") == "menu":
        return "scene_menu"
    if e.get("form") == "menu":
        return "partner_menu" if int(e["id"].split("_")[1]) <= 5 else "card_menu"
    return "dialogue"  # battle_001: if it draws at all, the battle text window is the dialogue window


def raw_rows(en):
    """A hand-written token string as its rows, tokens gone. A blank row counts; a trailing newline opens none."""
    rows = [TOKEN.sub("", r) for r in re.split(r"\{nl2?\}", en)]
    return rows[:-1] if len(rows) > 1 and not rows[-1] else rows


def raw_lint(e, en, name_px=0):
    """Rows and pixels against the entry's box. A fragment's first row follows a name of name_px at runtime."""
    box = WINDOWS[raw_box(e)]
    rows, bad = raw_rows(en), []
    if len(rows) > box["rows"]:
        bad.append(f"{len(rows)} rows, {raw_box(e)} holds {box['rows']}")
    for n, r in enumerate(rows):
        px = width(r) + (name_px if not n and e.get("form") == "fragment" else 0)
        if px > box["px"]:
            bad.append(f"{px} px, {raw_box(e)} holds {box['px']}: {r!r}")
    return bad


if __name__ == "__main__":
    # dry run: python -X utf8 tools/fit.py "text"  (2-row page under a name tag)
    for page in fill_rows(sys.argv[1], 2):
        print(page, [width(r) for r in page])
