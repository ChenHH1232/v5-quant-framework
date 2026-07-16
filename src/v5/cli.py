from __future__ import annotations

import argparse
import sys

from v5.cli_bank import register_bank_commands
from v5.cli_coal import register_coal_commands
from v5.cli_core import register_core_commands
from v5.cli_insurance import register_insurance_commands
from v5.cli_platform import register_platform_commands
from v5.cli_utilities import register_utilities_commands
from v5.engine import RunBlockedError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_core_commands(subparsers)
    register_bank_commands(subparsers)
    register_utilities_commands(subparsers)
    register_coal_commands(subparsers)
    register_insurance_commands(subparsers)
    register_platform_commands(subparsers)

    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (RunBlockedError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
