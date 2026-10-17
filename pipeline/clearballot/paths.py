"""Repository paths shared by all pipeline modules."""
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent
SOURCES = ROOT / "sources"
DATA = ROOT / "data"
CONTENT = ROOT / "content"
ALLOWLIST = ROOT / "allowlist.json"
