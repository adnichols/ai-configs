#!/usr/bin/env python3
"""Obsolete: pi-prewalk is now vendored under _pi/packages/pi-prewalk.

Named execution profiles (including the DeepSeek Flash default) live in
profiles.json. install.sh installs the stable local-packages mirror and no
longer patches npm:pi-prewalk.

This script remains only so older docs/callers fail closed with a clear message.
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    check = "--check" in argv
    msg = (
        "pi-prewalk is vendored at _pi/packages/pi-prewalk; "
        "edit profiles.json / extensions/prewalk.ts there instead of patching npm"
    )
    if check:
        print(f"pi-prewalk patch obsolete (ok): {msg}")
        return 0
    print(msg, file=sys.stderr)
    print("Run: ./install.sh --pi", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
