"""insert.py: write the hook, font and text into copies of the program files, and a layout that points at them.

    python -X utf8 tools/insert.py [--marker] [--qa ID=TEXT]...

Writes work/en/<program files>, work/layout_en.xml, work/en/vamap.tsv (old string address -> new) and work/en/writes.txt
(every write with the bytes it replaced, for romdiff.py). work/tree stays pristine: the identity test rebuilds from it.

Text comes from each entry's `en`, or stays Japanese where there is none. --marker replaces every line with its id and
filler text instead (phase 5); --qa overrides single entries in either mode (the width gate).

Each script block is repacked from its start and every reference follows the string: an entry's `refs` are the whole
list, so nothing else is rewritten (docs/re/text.md lists what must not be). A `common` entry stays inside its own span
in all eight overlays. A `menu` or `bark` entry stays where it is if it fits, else it moves into the script block.
"""
import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dte  # noqa: E402
import extract  # noqa: E402
import font  # noqa: E402
import jptext  # noqa: E402

ARMIPS = ROOT / "tools/armips/armips.exe"
EXE = "SLPS_010.15"
TOKEN = re.compile(r"(\{[^}]*\})")
ASCII_RUNS = re.compile(r"[ -~]+|[^ -~]+")
KEEP_FORMS = ("numbers", "debug", "memcard")
LINE_PX = 224  # measured: docs/re/engine.md
FOX = "The quick brown fox jumps over the lazy dog, then runs all the way back home again before it gets dark. "
SHORT_FORMS = ("menu", "choice", "fragment")


def encode(text, jp, dt):
    """Bytes for the game: tokens through jp.tbl, English through the pair table, anything else as the codec reads it.

    `{nl2}` becomes `{nl}`: the same newline, one byte less (0x8003A40C and 0x8003A47C both set state 5)."""
    out = bytearray()
    for part in TOKEN.split(text):
        if part.startswith("{"):
            out += jp.encode("{nl}" if part == "{nl2}" else part)
        else:
            for run in ASCII_RUNS.findall(part):  # a menu line mixes a fullwidth indent with English
                out += dt.pack(run) if run.isascii() else jp.encode(run)
    return bytes(out)


def short_id(eid):
    """syo01_123 -> 1.123, common_057 -> c57: an id that fits a menu row."""
    a, n = eid.split("_")
    return f"{int(a[3:])}.{int(n)}" if a.startswith("syo") else f"{a[0]}{int(n)}"


def filler(px, fnt, start=0):
    out = ""
    for ch in FOX[start:] + FOX:
        if fnt.width(out + ch) > px:
            break
        out += ch
    return out.rstrip(" ") or "x"


def marker_text(e, fnt, px=LINE_PX):
    """The entry's own tokens, with its id and filler where its text was."""
    if e.get("form") == "name":
        return f"{short_id(e['id'])}{{end}}"
    if e.get("form") == "battle":
        return "BATTLE{end}"
    out, in_tag, first = [], False, True
    for part in TOKEN.split(e["jp"]):
        if not part:
            continue
        if part.startswith("{"):
            in_tag = part == "{nameon}" or (in_tag and part != "{nameoff}")
            out.append(part)
        elif in_tag:
            m = re.match(r"\d\d", part)
            out.append((m.group(0) if m else "") + "Name")
        elif e.get("form") in SHORT_FORMS:
            lead = part[:len(part) - len(part.lstrip("　"))]  # a menu's fullwidth indent is where the cursor sits
            out.append(lead + (f"[{short_id(e['id'])}]" if first else "x" * max(1, len(part) - len(lead))))
            first = False
        else:
            head = f"[{short_id(e['id'])}] " if first else ""
            out.append(head + filler(px - fnt.width(head), fnt, 0 if first else 40))
            first = False
    return "".join(out)


def lui_map(d):
    """{index of a low instruction: index of the lui it reads}, the same pairing rule as mips.lui_pairs."""
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    out = {}
    for i, w in enumerate(words):
        if w >> 26 != 0x0F:
            continue
        rt = (w >> 16) & 31
        for j in range(i + 1, min(i + 17, n)):
            x = words[j]
            op, rs, rt2 = x >> 26, (x >> 21) & 31, (x >> 16) & 31
            if rs == rt and op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                out[j] = i
            if (op == 0x0F and rt2 == rt) or (op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25) and rt2 == rt):
                break
    return out


class Writer:
    """One file's copy; every write is logged with the original bytes it replaces (romdiff.py --writes)."""

    def __init__(self, name, orig):
        self.name, self.orig, self.d, self.log = name, bytes(orig), bytearray(orig), []

    def put(self, off, data, by):
        self.log.append(f"{off:X} {self.orig[off:off + len(data)].hex()} {bytes(data).hex()} {by}")
        self.d[off:off + len(data)] = data


def load_entries():
    """{program: [entries]}; shared entries appear under each overlay."""
    docs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "script").glob("*.json"))}
    return {n: docs[n]["entries"] + (docs["common"]["entries"] if n in extract.SCRIPTS else [])
            for n in docs if n != "common"}


def text_of(e, mode, qa, fnt, px):
    """The entry's new text, or None to leave its bytes alone."""
    if e["id"] in qa:
        return qa[e["id"]]
    if e.get("data") or e.get("form") in KEEP_FORMS:
        return None
    if mode == "marker":
        return marker_text(e, fnt, px)
    return e.get("en", e["jp"])


class Pool:
    """Free bytes in one span: the span minus the entries that stay put."""

    def __init__(self, a, b, kept):
        self.free, pos = [], a
        for o, s in sorted(kept):
            if o > pos:
                self.free.append([pos, o])
            pos = max(pos, o + s)
        if pos < b:
            self.free.append([pos, b])

    def take(self, size):
        for span in self.free:
            if span[1] - span[0] >= size:
                span[0] += size
                return span[0] - size
        return None

    def left(self):
        return sum(b - a for a, b in self.free)


def repack(name, orig, entries, ranges, jp, dt, mode, qa, fnt, px):
    """Returns (Writer, {old va: new va}, bytes left). Raises when text doesn't fit or a lui can't follow."""
    base = extract.base_of(name)
    w = Writer(name, orig)
    spans = [(a, b, r) for a, b, r, _n in ranges.get(name, [])]
    def off(e):
        return int(e["off"], 16)

    def span_of(o):
        return next(s for s in spans if s[0] <= o < s[1])

    new = []
    for e in entries:
        t = text_of(e, mode, qa, fnt, px)
        if t is None:
            continue
        if e.get("dead") and e.get("no_end"):  # a retired head: code enters after it, so it needs no bytes
            new.append((e, None))
        else:
            new.append((e, encode(t, jp, dt)))
    moving = {e["id"] for e, _ in new}
    kept = [(off(e), e["size"]) for e in entries if e["id"] not in moving]

    def blank_slots():
        for e, _b in new:
            if w.orig[off(e):off(e) + e["size"]].count(0) != e["size"]:
                w.put(off(e), bytes(e["size"]), f"vacate {e['id']}")

    pools = {}

    def pool(span):
        if span not in pools:
            pools[span] = Pool(span[0], span[1], [k for k in kept if span[0] <= k[0] < span[1]])
        return pools[span]

    main = [s for s in spans if s[2] == "script"]
    placed = {}
    # common spans and in-place slots first; what does not fit goes after the script, which the block's end checks
    later = []
    for e, b in new:
        if b is None:
            continue
        s = span_of(off(e))
        if s[2] in ("common", "names", "prompt"):
            at = pool(s).take(len(b))
            if at is None:
                raise ValueError(f"{name}: {e['id']} doesn't fit its {s[2]} span ({len(b)} bytes, {pool(s).left()} left)")
            placed[e["id"]] = at
        elif s[2] == "script":
            later.append((e, b))
        elif len(b) <= e["size"]:
            placed[e["id"]] = off(e)
        else:
            later.append((e, b))
    later.sort(key=lambda x: (span_of(off(x[0]))[2] != "script", off(x[0])))
    for e, b in later:
        at = pool(main[0]).take(len(b)) if main else None
        if at is None:
            raise OverflowError(f"{name}: script block is full at {e['id']}: {len(b)} bytes, "
                                f"{sum(len(x[1]) for x in later)} wanted, {main[0][1] - main[0][0] if main else 0} there")
        placed[e["id"]] = at

    blank_slots()
    vamap, lui_of = {}, lui_map(orig)
    hi_wanted = {}
    for e, b in new:
        if b is None:
            continue
        at = placed[e["id"]]
        w.put(at, b, f"text {e['id']}")
        vamap[base + off(e)] = base + at
        for r in e.get("refs", ()):
            if r.get("file", name + ".BIN") not in (f"{name}.BIN", tree_name(name)):
                continue
            site, target = int(r["site"], 16) - base, base + at + r["delta"]
            if r["kind"] == "word":
                w.put(site, struct.pack("<I", target), f"word {e['id']}")
                continue
            word = struct.unpack_from("<I", orig, site)[0]
            if word >> 26 != 0x09:
                raise ValueError(f"{name} {site + base:#x}: reference is not an addiu")
            w.put(site, struct.pack("<I", (word & 0xFFFF0000) | (target & 0xFFFF)), f"lo {e['id']}")
            hi_wanted.setdefault(lui_of[site // 4], set()).add((target + 0x8000) >> 16 & 0xFFFF)

    # a lui that keeps its value is fine whoever else reads it; one that changes must have only text readers
    readers = {}
    for low, lui in lui_of.items():
        readers.setdefault(lui, []).append(low)
    text_sites = {int(r["site"], 16) - base for e, b in new if b is not None for r in e.get("refs", ())
                  if r["kind"] == "code" and r.get("file", name + ".BIN") in (f"{name}.BIN", tree_name(name))}
    for lui, his in hi_wanted.items():
        word = struct.unpack_from("<I", orig, lui * 4)[0]
        if len(his) > 1:
            raise ValueError(f"{name}: lui at {base + lui * 4:#x} would need {sorted(hex(h) for h in his)}")
        hi = his.pop()
        if hi == word & 0xFFFF:
            continue
        others = [low for low in readers[lui] if low * 4 not in text_sites]
        if others:
            raise ValueError(f"{name}: lui at {base + lui * 4:#x} must change for text but also serves "
                             f"{[hex(base + x * 4) for x in others]}")
        w.put(lui * 4, struct.pack("<I", (word & 0xFFFF0000) | hi), "hi")
    return w, vamap, {s[0]: pool(s).left() for s in main}


def tree_name(name):
    return Path(extract.tree_path(name)).name


def assemble(out, dt):
    """Hook, font and pair table into out/SLPS_010.15."""
    (out / "font.bin").write_bytes(font.Font().blob())
    (out / "dte.bin").write_bytes(dt.blob())
    exe = out / EXE
    exe.write_bytes((extract.TREE / EXE).read_bytes())
    r = subprocess.run([str(ARMIPS), "-strequ", "EXE", str(exe), "-strequ", "FONT", str(out / "font.bin"),
                        "-strequ", "DTE", str(out / "dte.bin"), "-sym", str(out / "vwf.sym"), str(ROOT / "asm/vwf.asm")],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"armips failed:\n{r.stdout}{r.stderr}")


def write_layout(out, files):
    """layout.xml with the changed files' source pointing at out/."""
    xml = (ROOT / "work/layout.xml").read_text(encoding="utf-8")
    for tree_rel in files:
        tag = f'<file name="{Path(tree_rel).name}" type="data"'
        if xml.count(tag) != 1:
            raise ValueError(f"{tag} found {xml.count(tag)} times in layout.xml")
        xml = xml.replace(tag, f'<file name="{Path(tree_rel).name}" source="{(out / tree_rel).as_posix()}" type="data"')
    path = out.parent / f"layout_{out.name}.xml"  # beside out/: a test's temp build never touches work/layout_en.xml
    path.write_text(xml, encoding="utf-8", newline="\n")
    return path


def fit_marker_width(name, orig, entries, ranges, jp, dt, qa, fnt):
    """Widest filler that fits this overlay's script block."""
    for px in range(LINE_PX, 0, -8):
        try:
            return repack(name, orig, entries, ranges, jp, dt, "marker", qa, fnt, px) + (px,)
        except OverflowError:
            continue
    raise OverflowError(f"{name}: no marker fits")


def insert(out=None, mode="en", qa=None, quiet=False):
    out = Path(out or ROOT / "work/en")
    out.mkdir(parents=True, exist_ok=True)
    qa = qa or {}
    jp, fnt, ranges, dt = jptext.Jp(), font.Font(), extract.load_ranges(), dte.Dte()
    assemble(out, dt)
    logs, vamap, changed = [], {}, [EXE]
    for name, entries in load_entries().items():
        tree_rel = extract.tree_path(name)
        if name == "SLPS_010":
            if mode == "en":
                w = Writer(name, (extract.TREE / EXE).read_bytes())
                w.d = bytearray((out / EXE).read_bytes())  # the assembled hook stays; the log's old bytes are the disc's
                for e in entries:
                    if "en" in e:  # the memory-card title: the BIOS draws it, Shift-JIS only
                        data = e["en"].replace("{end}", "").encode("cp932") + b"\0"
                        if len(data) > e["size"]:
                            raise ValueError(f"{e['id']}: {len(data)} bytes, its span holds {e['size']}")
                        w.put(int(e["off"], 16), data, f"title {e['id']}")
                (out / EXE).write_bytes(w.d)
                logs += [f"{name} {ln}" for ln in w.log]
            continue
        orig = (extract.TREE / tree_rel).read_bytes()
        if not any(text_of(e, mode, qa, fnt, LINE_PX) is not None for e in entries):
            continue
        if mode == "marker" and name in extract.SCRIPTS:
            w, vm, left, px = fit_marker_width(name, orig, entries, ranges, jp, dt, qa, fnt)
        else:
            w, vm, left = repack(name, orig, entries, ranges, jp, dt, mode, qa, fnt, LINE_PX)
            px = LINE_PX
        path = out / tree_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(w.d)
        changed.append(tree_rel)
        logs += [f"{name} {ln}" for ln in w.log]
        vamap.update(vm)
        if not quiet:
            print(f"{name}: {len(w.log)} writes, script block left {sum(left.values())} bytes, marker px {px}")
    (out / "writes.txt").write_text("\n".join(logs) + "\n", encoding="utf-8", newline="\n")
    (out / "vamap.tsv").write_text("".join(f"{a:#x}\t{b:#x}\n" for a, b in sorted(vamap.items())),
                                   encoding="utf-8", newline="\n")
    return write_layout(out, changed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT")
    a = ap.parse_args()
    print(insert(mode="marker" if a.marker else "en", qa=dict(q.split("=", 1) for q in a.qa)))
