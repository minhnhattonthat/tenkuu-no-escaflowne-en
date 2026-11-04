# Visual-QA reviewer brief - Tenkuu no Escaflowne (PS1)

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything
except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- Optional: the original ROM's sheets (`work/qa/tour_jp/`, same ids) and `glossary.md`.

## How to look
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 $SKILL/scripts/sheet.py SHEET.png --crop x,y,w,h --zoom 3 --out <scratch>.png` and read that.
- When something looks wrong, open the same id from `tour_jp/` (`sheet.py EN.png --compare JP.png`). If the
  original shows the same thing, it is the game's own behaviour: `ok`, with a note.

## Judge
An `issue` is any of:
- Japanese still visible;
- text overflowing a box, clipped by a frame, or running off screen;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok` (the controller adds the game's own below):
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a map or scene still loading after a warp;
- anything identical in the original's sheet.
- the `奉` on the chapter 1 shrine box (scenery, left Japanese by default).
- a page ending on a comma or mid-sentence: all 65 such ends in the script sit on the JP's own page break, usually a
  voice clip's boundary, so the split can't move (checked in the script, not one by one on screen). A one-word row that opens its own voice clip likewise (`syo04_153`).
- the choice cursor's tail crossing the prompt row above option 1 (same on the JP frame, `choice_box`).
- redrawn art judged as art, not pixel by pixel against the original: the title's star and glow behind the logo, and the
  opening video's logo, which has no glare behind it (`docs/re/graphics.md`). Still an issue if it strikes across letters.
- a name tag "Van" over the lion-faced bust in `ch7_s56` (JP tags it バァン too); the HUD's small English labels such as
  the one in `ch4_s74` are the original art, untouched.

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.
