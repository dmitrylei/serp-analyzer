"""CLI helper to run Streamlit UI."""

from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> None:
    if not shutil.which("streamlit"):
        print("streamlit is not installed. Run: pip install -e .")
        sys.exit(1)
    cmd = ["streamlit", "run", "src/serp_monitor/ui/app.py"]
    raise SystemExit(subprocess.call(cmd))
