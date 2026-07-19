from __future__ import annotations

import argparse
from pathlib import Path

from v5.port_rail_operating_evidence_runner import classify_port_rail_eastmoney_segments
from v5.port_rail_operating_state_runner import build_port_rail_operating_state_panel


def register_port_rail_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("build-port-rail-operating-state-panel")
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("\u6570\u636e\u5e93") / "processed" / "port_rail_operating_state_v55b")
    parser.set_defaults(handler=_handle_build_port_rail_operating_state_panel)

    classify_parser = subparsers.add_parser("classify-port-rail-eastmoney-segments")
    classify_parser.add_argument("raw_csv", type=Path)
    classify_parser.add_argument("disclosure_csv", type=Path)
    classify_parser.add_argument("--out-dir", type=Path, default=Path("\u6570\u636e\u5e93") / "processed" / "port_rail_operating_evidence_v55h")
    classify_parser.set_defaults(handler=_handle_classify_port_rail_eastmoney_segments)


def _handle_build_port_rail_operating_state_panel(args: argparse.Namespace) -> int:
    print(build_port_rail_operating_state_panel(args.panel, args.out_dir))
    return 0


def _handle_classify_port_rail_eastmoney_segments(args: argparse.Namespace) -> int:
    print(classify_port_rail_eastmoney_segments(args.raw_csv, args.disclosure_csv, args.out_dir))
    return 0
