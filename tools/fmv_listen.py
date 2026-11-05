"""fmv_listen.py: dump each video's XA audio and transcribe it, the first step of subtitling (docs/re/fmv-subs.md).

    python -X utf8 tools/fmv_listen.py [SC02 ...]    writes work/fmv/audio/*.wav, work/fmv/asr/*.json (kept if present)

Needs work/jp.idx, Java and faster-whisper. VAD stays off: with it on, lines over music go missing.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "tools/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar"
AUDIO, ASR = ROOT / "work/fmv/audio", ROOT / "work/fmv/asr"


def xa_items():
    """{video name: index number of its XA item} from the jPSXdec index."""
    pattern = re.compile(r"^#:(\d+)\|ID:ESCA/STR/\d+/(\w+)\.STR\[0\.0\]\|.*Type:XA")
    return {m[2]: m[1] for line in (ROOT / "work/jp.idx").read_text(encoding="utf-8").splitlines() if (m := pattern.match(line))}


def main(names):
    items = xa_items()
    AUDIO.mkdir(parents=True, exist_ok=True)
    ASR.mkdir(parents=True, exist_ok=True)
    model = None
    for name in names or sorted(items):
        out = ASR / f"{name}.json"
        if out.exists():
            continue
        wavs = list(AUDIO.rglob(f"{name}.STR*.wav"))
        if not wavs:
            subprocess.run(["java", "-jar", str(JAR), "-x", str(ROOT / "work/jp.idx"), "-i", items[name], "-dir", str(AUDIO)], cwd=ROOT, check=True, capture_output=True)
            wavs = list(AUDIO.rglob(f"{name}.STR*.wav"))
        assert len(wavs) == 1, (name, wavs)
        model = model or WhisperModel("large-v3", device="cpu", compute_type="int8")
        # decoded here because faster-whisper's own decode breaks on this machine's PyAV
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wavs[0]), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], check=True, capture_output=True).stdout
        segments, _ = model.transcribe(np.frombuffer(pcm, np.float32), language="ja", vad_filter=False, condition_on_previous_text=False, word_timestamps=True, beam_size=5)
        rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(), "no_speech": round(s.no_speech_prob, 2), "logprob": round(s.avg_logprob, 2)} for s in segments]
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
        print(name, len(rows), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
