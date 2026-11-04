"""The dump pin works: a listing with a wrong hash is refused."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom


def test_wrong_hash_refused(tmp_path):
    rom = tmp_path / "x.bin"
    rom.write_bytes(b"x")
    listing = tmp_path / "rom.sha1"
    listing.write_text("0" * 40 + "  " + str(rom) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        check_rom.check(listing)


@pytest.mark.skipif(not (ROOT / "rom").is_dir(), reason="no dump")
def test_dump_matches():
    check_rom.check()
