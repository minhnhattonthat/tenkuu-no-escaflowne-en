# Phase 9 story pass

- **Reader:** a fresh session that hadn't written the script, in one read-only pass of every chapter file (`tools/pairs.py`) in story order, against `docs/synopsis.md`, `docs/style-reference.md` and `glossary.md`.
- **Not independent in the full sense:** same model family. Nested workers are refused in this run and `codex exec` is over its limit until 2026-11-11 (retried this session).
- **Coverage:** every line of `common`, `BATTLE`, `SYO01`-`SYO07`. Verdicts: `work/qa/story/verdicts/phase9.tsv`.

## Found and fixed (`work/tl/r06`)
| Rating | id | Problem |
|---|---|---|
| Important | syo02_311 | 姿が見えようが is about Van seeing the stealth units after his river trick. "Even if I can see you" had it backwards: Zaibach could always see Van. Now "So what if you can see us?" |
| Minor | syo02_124 | "Not here, fighting here...!" read as garbled |
| Minor | syo02_169 | "Can't Merle and you ever go back" for メルル達 was stiff |
| Minor | syo03_176 | 残念です as "It's a pity." was flat for a boy betrayed |
| Minor | syo03_236 | "To your heartbeat!" unclear: Millerna is teaching CPR |
| Minor | syo03_253 | "One proves one's own innocence oneself." was stilted |
| Minor | syo04_310 | "Lend me, Folken, your strength." was awkward |
| Minor | syo04_450 | "My will back then" flattened Leon's love for the girl: 想い between people is "feelings", per the glossary |
| Minor | syo05_099, 101 | Allen's "O-okay!" off voice; "You're Refine!" stiff |
| Minor | syo05_215 | 想い between people: "feelings" |
| Minor | syo06_151, 152 | Grandma's 想いは叶う is the callback to syo03_346 "wish": now "wish", not "will" |
| Minor | syo06_207 | 想い is about Hitomi's own feelings: "feelings" |
| Minor | syo06_243 | "Do you hate me, Folken Fanel?" read as if Van were Folken Fanel |
| Minor | syo07_129 | "my will got through" against Merle's "your feelings" one line back |
| Minor | syo07_205 | "Have faith in him" lost the echo of Grandma's "Believe in him" |

## Checked and fine
No reveal comes early: Dilandau stays "he" until syo07_290, and Chid's parentage and Isaac's identity land where the synopsis says. Merle's third person, Dryden's looseness, Dornkirk's no-contractions, Dilandau's vowels, the Ispano pidgin and Mole Man's dropped letters stay steady. Running jokes keep their punchlines: Narita divorce, "a friend of mine" (both ways), "I want you / your power", the birdcage, "a cat, of all things".

## Verdict
No Critical or Important left. `docs/polish.md` closed: three lines waived with reasons. A web search found no official form for the fleet names or ジェチア.
