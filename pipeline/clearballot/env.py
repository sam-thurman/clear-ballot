"""Load KEY=value pairs from the repository .env into os.environ (without overriding
values already set). No third-party dependency; values are never printed."""
from __future__ import annotations

import os

from .paths import ROOT


def load_env(path=ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
