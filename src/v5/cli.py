from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from v5.engine import RunBlockedError, run_strategy, validate_spec_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("spec", type=Path)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("spec", type=Path)
    run_parser.add_argument("--out", type=Path, default=Path("experiments"))
    run_parser.add_argument("--allow-blockers", action="store_true")

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            result = validate_spec_file(args.spec)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["audit"]["passed"] else 2
        if args.command == "run":
            run_dir = run_strategy(args.spec, args.out, allow_blockers=args.allow_blockers)
            print(str(run_dir))
            return 0
    except RunBlockedError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

