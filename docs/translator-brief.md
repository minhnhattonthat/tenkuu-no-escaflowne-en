# Translator brief - Tenkuu no Escaflowne (PS1)

You translate part of the Japanese script of Tenkuu no Escaflowne into English for a fan patch. It retells the anime: serious fantasy drama, with a schoolgirl from Earth and a young king at its centre.
Work only on the batches named in your dispatch, one at a time in the order given, each to a passing check before the next. Do all translation yourself; do not dispatch subagents.

## Read first
1. `docs/style-reference.md` - character voices and approved example pairs. Match this voice.
2. `glossary.md` - binding names and terms, its rulings and style rules first.
3. `docs/synopsis.md` - plot, routes, who is who and the late reveals. Don't give a reveal away early; keep early lines consistent with what comes later.

## Input: `work/tl/<batch>.tsv`
`id<TAB>speaker<TAB>form<TAB>Japanese` - form is dlg | choice | narration; ` / ` is a JP row break (ignore it, the fitter
wraps), ` | ` a page break, ` ^ ` a voice clip on a new row, ` # ` a choice option: keep the same ` | `, ` ^ `, ` # ` in your
English. Text that outgrows its page runs on to an extra page by itself. Lines are in story order:
use neighbours for context. Some lines are fragments of one sentence split by effects - make the pieces read in sequence.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (not a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII: straight quotes, `...`, `--`; no tabs inside
the English, no Japanese or fullwidth characters, no `\uXXXX`. Write `\n` only where a break must fall (rare).

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every reported id until it prints OK.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details the Japanese doesn't
  state; don't summarise or skip. Adapt wordplay so the joke still lands (no translator notes).
- Keep the speaker audible. JP register markers carry voice and must turn into English devices, not vanish:
  old men's じゃ/のう/わし ("eh?", "my boy", "back in my day"), rough men's ぜ/ねぇ/っス ("ain't", "ya", "dammit",
  clipped grammar), feminine かしら/わよ/のね ("I wonder...", "you know", "dear"), whines and drawls (〜ぅ/なぁ:
  "but Mooom", stretched words). A line any speaker could have said is a mistake.
- Use names and terms exactly as in the glossary. Never abbreviate to fit. If a line can't fit the limit without
  losing meaning, keep the meaning and report it as `LONG: id`.
- Honorifics kept, hyphenated (Van-sama, Hitomi-san, Boris-dono, senpai). Name order: given name first.
  Punctuation: a line opening with 「 is speech: "...", closed at the end of the entry; no 「: a thought or aside, no
  quotes. 『』 -> '...', ・・・ and … -> `...`, ！？ -> `?!`. Emphasis: capitals, sparingly.
- Placeholders/control codes: copy every one exactly; no suffixes glued to a variable (write "No. [n]" not "[n]th"),
  no a/an right before a name variable.
- Mistakes earlier reviews caught; don't repeat them:
  - はい follows what was asked: hypnotised Hitomi answering Plakt is "Yes...", not "All right...".
  - Check whose story a line is about: syo04_226 とんだ有名人 mocks Leon, not the speaker Allen.
  - One-word rules with no check behind them: 運命 is "fate" (`glossary.md`); 引力 is "attraction"; 生体実験 is "human
    experiments"; 想い is "will", "wish" or "feelings" by the rule in `glossary.md`, and an echo of a line keeps its word.
  - Voices flatten first where a line is only information: Mole Man's "Saw her at the harbor, I did", Millerna's "you
    know" and "Why, of course". Dornkirk uses no contractions.
  - `batches.py check` refuses an added page holding 3 words or fewer: reword the line, don't cut meaning.

## Consistency
Never edit `glossary.md`. For a recurring name or term not in it, pick a form, use it consistently, and report it.

## Report (reply with only this)
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
