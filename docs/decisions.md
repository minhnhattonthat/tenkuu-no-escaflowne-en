# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-04 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western order (given name first). Owner's standing answer for one-shot runs. |
| D2 | 2026-11-04 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist, else an earlier fan patch, else Hepburn without macrons. |
| D3 | 2026-11-04 | Credits | stay Japanese, translate | English. |
| D4 | 2026-11-04 | Abbreviations | engine work first (default), abbreviate | Skill default: engine work first; abbreviate only as a flagged last resort. |
| D5 | 2026-11-04 | Graphics text left in Japanese | none (default), list | Translate all (titles, menus, banners, cards). Keep the original Japanese logo only if it has no official English version. |
| D6 | 2026-11-04 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through every checkpoint. Never run `gh release create`, never change repo visibility; the run ends at a built and verified release zip. |
| D7 | 2026-11-04 | Existing saves, memory cards, savestates | provide, none | None provided; build the debug tool as usual. |
| D8 | 2026-11-05 | Subtitles for videos | leave unsubtitled (old default), subtitle those with spoken dialogue | Subtitle every video with dialogue voice, burned in. Songs stay unsubtitled by default: the ask names dialogue, and the user resumed without changing it when told. `docs/re/fmv-subs.md`. |
| D9 | 2026-11-05 | Publishing | v1.1 public, v1.0 public, private release only | v1.1 public, knowing the patch holds about 6 minutes of re-encoded video frames (91 MB). Lifts D6's bar on `gh release create` and repo visibility for this release. |

## Open questions (no ruling yet; defaults in force)

- **D2 amendment, game-original names.** `glossary.md` adds a rule D2 doesn't have: a katakana name that plainly transcribes a foreign word uses that word (Dilate, Rampant, Refine). Options: keep the rule; strict Hepburn for all of them; keep it but use "Lefine" for レフィーヌ, whose "Refine" reads like the verb. Default: keep the rule, "Refine" stays. Changing the name is one edit in `glossary.md` and `tbl/names.tsv` plus 5 lines.
