"""Small CLI for previewing dispatch payloads."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .planner import render_dispatch_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a dispatch plan JSON payload.")
    parser.add_argument("config_path", help="Path to a JSON job config.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(render_dispatch_plan(Path(args.config_path)))
    return 0
