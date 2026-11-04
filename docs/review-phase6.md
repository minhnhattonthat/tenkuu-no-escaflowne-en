# Phase 6 review

- **Reader:** the implementer, in a read-only pass of `work/qa/story/chapters/*` (`tools/pairs.py`), against `glossary.md`. **Not independent:** nested workers are refused in this run and `codex exec` is over its usage limit until 2026-11-11. Phase 9's story pass needs an independent reader.
- **Coverage:** all of `common`, `SYO01`-`SYO06`, `SYO07` up to syo07_151. syo07_152-333 (b021, b022) were written in the same session and only re-read while authoring, so they got the weakest check.

## Second read (`work/tl/r04`)
- **Reader:** the phase 6 external review (`.harness/reviews/`, 35% of lines by hand) and then a fresh session that didn't write the script, for the remaining chapters: all of `SYO01`, `SYO02`, `common` in full; the rest of `SYO03`, `SYO04`, `SYO06`, `SYO07` skipping lines under 12 JP characters and choice boxes. So every non-choice line of 12+ JP characters got a read other than its author's; shorter lines and choice boxes outside those chapters had script checks only.
- **Still not independent in the full sense:** same model family, and `codex exec` is over its limit until 2026-11-11. Phase 9's story pass should use a different reader if one exists by then.
- **Fixed:** 15 added pages holding a scrap (now refused by `fit.py`); Mole Man and Millerna voice lines; Dilandau's drawn-out vowels (syo01_366, syo02_127, 164, syo07_069, 095); Dornkirk's contractions; 想い on syo07_043, 322, 323, syo04_416; syo07_182, 234, 295, syo05_184.
- **Result:** no Critical or Important left in the lines read. `fit.py` also pulls a word down so no page ends on a one-word row.

## Found and fixed (`work/tl/r01`, `r02`, `r03`)
| Rating | ids | Problem |
|---|---|---|
| Important | syo03_195, 199, 217 | Hypnotised Hitomi's はい as "All right...": she's answering questions, now "Yes..." |
| Important | 16 lines in SYO03, SYO06, SYO07 | 運命 drifted between "fate" and "destiny"; now "fate" (rule in `glossary.md`) |
| Important | syo07_147 | 引力 callback to Dornkirk's speech lost ("the pull"); now "attraction" |
| Important | syo04_226 | とんだ有名人 is about Leon, not Allen: "What a fine reputation I have" was wrong |
| Important | syo07_145, 146 | 生体実験 as "living experiments"; now "human experiments" |
| Minor, fixed | syo01_305, 344; syo02_013, 110, 115, 302, 321; syo03_005, 015, 212; syo04_454; syo05_009, 032; syo06_069, 074, 075, 076 | Awkward lines, doubled titles, an added clause, "Why on earth" from Dornkirk |

## Verdict
No Critical or Important issue left from this read. Minors left: `docs/polish.md`.
