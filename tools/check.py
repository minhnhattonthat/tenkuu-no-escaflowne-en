"""check.py: the one-command check (tests + lint); the pre-commit hook runs this. Exit code gates the commit."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# no:faulthandler: on Windows it prints a "fatal exception" for each access violation unicorn raises and handles itself
sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-rs", "-p", "no:faulthandler", "tests"], cwd=ROOT))
