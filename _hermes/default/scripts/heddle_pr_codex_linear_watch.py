#!/usr/bin/env python3
"""Compatibility wrapper for the reusable autobuild PR nudge monitor."""
from pathlib import Path
import runpy

runpy.run_path(str(Path.home() / ".hermes" / "scripts" / "autobuild_pr_nudge_monitor.py"), run_name="__main__")
