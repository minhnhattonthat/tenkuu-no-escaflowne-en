# Video subtitles

37 of the 57 videos carry burned-in English (201 lines, 5,632 frames): `data/fmv_subs.tsv`, burned by `tools/fmv_subs.py`, called from `gfx.edited()`. FMV id n plays `SCn.STR` (0x2C, 0x37, 0x38 are the endings SC44, SC55, SC56; the `ending_tie`, `ending_b`, `ending_a` warps were seen playing those three).

**Source of the Japanese:** no script exists on disc, so `tools/fmv_listen.py` transcribes the XA audio with faster-whisper large-v3 (CPU, VAD off), one line per segment in `work/fmv/asr/`. A second pass with the character names as prompt checked the doubtful clips. The `ja` column is the corrected reading, not raw output. No human has checked it by ear.

**Corrected by context, not by the transcript:** `SC12` 深く→不覚, `SC39` kept as heard (上空に先行, could be 閃光), `SC43` 疲れ合う→惹かれ合う, `SC46` 次ぐ→告ぐ, `SC52` 経験以上→計器異常, `SC53` 浮遊要素→浮遊要塞, `SC49` チリュウ→地竜. Cut-off lines finished in English by inference: `SC36` もう一度お前に ("I want to see you").

**Left out on purpose:**
- `SC01` opening song, sung only (no lyric subtitles).
- Hallucinated `ご視聴ありがとうございました`, which Whisper emits over music: `BANDAI`, SC04, 08, 15, 16, 18, 22, 26, 28, 29, 32, 33.
- Screams, grunts, breathing: `SC11`, `SC25`, `SC34`, `SC50`.
- Too doubtful to subtitle: `SC34` 6-9 s (garbled, gone in pass 2), `SC39` ロン, `SC43` アトランティスマシーン 15.7-23.8 s (long span, low confidence), `SC51` バァン (only with the name prompt).

**Limits:** the 15 fps frames under a line are re-encoded from a decode, so they lose a little quality and can pop faintly at the line's edges. Size, sectors and audio are untouched (`tests/test_gfx.py`).
