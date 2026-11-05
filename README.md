# Tenkuu no Escaflowne (The Vision of Escaflowne) English translation

Unofficial English fan translation of **Tenkuu no Escaflowne** (PlayStation, Bandai, 1997): the source text and tools
that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue and story | Translated |
| Menus and system messages | Translated |
| Title screen, chapter cards, opening video's logo | Translated |
| Staff roll | Translated |
| Spoken video dialogue (37 of 57 videos) | English subtitles under Japanese speech; songs not subtitled |
| Voiced lines | Japanese audio under English text |

Tested in PCSX-Redux on a Japanese BIOS, from a cold boot. The game has no name entry and no option screen.

Known limits:

- Long lines run on to extra pages. Voice clips are timed to the Japanese pages, and nobody has checked by ear that they still line up.
- The glare over the logo in the opening video is missing.
- The shrine box in chapter 1's map art keeps its Japanese character, as scenery.
- Names the game invented, with no official spelling to follow, are best guesses: Jechia, Getin, Helio, Zodia, Gimle, Theo, Dilate, Rampant, Godashim, Zegu, Kaja, Refine.
- Saves from the unpatched game haven't been tried on the patched one.

See also [Issues](../../issues).

## Base dump

Tenkuu no Escaflowne (Japan), SLPS-01015. The patch applies to Track 1 only; keep your Track 2 and your .cue.

| Track | Size | MD5 | SHA-1 |
|---|---|---|---|
| 1 | 515,612,496 bytes | `28f82df7fedcf5bcd719d793b7679e64` | `4083350077d56992c714d2ed90a23a5e57ac3b72` |
| 2 | 32,986,800 bytes | `140001a90c546f8c20b644dbbac32ae6` | `5c876b512b0b57ca4ccc5fa2f8ee285788d56c7d` |

CRC32s and the patched hashes are in the README inside the release zip.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.claude/agents/` | Subagent types (translator, reviewer, visual QA, playtester) with only the tools each needs. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/tenkuu-no-escaflowne-en
cd tenkuu-no-escaflowne-en
# copy your dump to rom/: "Tenkuu no Escaflowne (Japan).cue" and its two tracks
#   (hashes above; the build refuses any other dump, see rom.sha1)
# fetch the tools listed in AGENTS.md (mkpsxiso, armips, jPSXdec + Java, PCSX-Redux for the tests)
python -X utf8 tools/unpack.py                         # -> work/tree, work/layout.xml
python -X utf8 tools/build.py                          # -> build/escaflowne_en.bin + .cue
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is the game publisher's and is included
only so the translation can be checked against it. Tenkuu no Escaflowne is (c) Sunrise, TV Tokyo and Bandai; this
project is not affiliated with them. Do not share patched images.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
