"""Every video subtitle fits two rows on screen, is in order and burns only into the bottom of the frame."""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fmv_subs  # noqa: E402


def test_lines_fit_and_are_in_order():
    for video, rows in fmv_subs.load().items():
        last = 0.0
        for start, end, en in rows:
            assert last <= start < end, (video, en)
            assert en.isascii() and en == en.strip(), (video, en)
            assert len(fmv_subs.wrap(en)) <= 2, (video, en)
            last = end


def test_wrap_refuses_a_third_row():
    try:
        fmv_subs.wrap("word " * 80)
    except ValueError:
        return
    raise AssertionError("no error for an oversized line")


def test_burn_stays_low_and_inside_the_frame():
    img = Image.new("RGB", (320, 240), (40, 90, 160))
    before = img.copy()
    fmv_subs.burn(img, "Finding happiness through a fate run by a machine is wrong!")
    box = Image.eval(Image.frombytes("L", img.size, bytes(a != b for a, b in zip(img.convert("L").tobytes(), before.convert("L").tobytes()))), lambda v: v * 255).getbbox()
    assert box and box[1] >= 180 and box[3] <= 230 and box[0] >= 4 and box[2] <= 316


def test_frames_follow_the_disc_rate():
    assert list(fmv_subs.frames_of(1.0, 1.2)) == [14, 15, 16, 17]
