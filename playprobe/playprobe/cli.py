"""PlayProbe CLI: explore a build for issues, diff two runs."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .build import load_build
from .diff import diff_findings, load_run
from .explorer import explore
from .report import render_diff_console, render_diff_markdown, render_explore_console


def cmd_explore(args: argparse.Namespace) -> int:
    build = load_build(args.build)
    result = explore(build, seed=args.seed, max_steps=args.max_steps)
    payload = result.to_dict()
    print(render_explore_console(payload), end="")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"Wrote {args.out}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    run_a = load_run(args.run_a)
    run_b = load_run(args.run_b)
    diff = diff_findings(run_a, run_b)
    print(render_diff_console(diff), end="")
    if args.out:
        markdown = render_diff_markdown(
            diff, run_a.get("build_name", args.run_a), run_b.get("build_name", args.run_b)
        )
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"Wrote {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playprobe", description="Self-serve AI playtesting bot (local MVP scaffold)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    explore_parser = subparsers.add_parser("explore", help="Run the exploration bot against a build graph.")
    explore_parser.add_argument("build", help="Path to a build graph JSON file.")
    explore_parser.add_argument("--seed", type=int, default=1, help="RNG seed for the exploration bot (default: 1).")
    explore_parser.add_argument(
        "--max-steps", type=int, default=500, help="Max steps the bot may take (default: 500)."
    )
    explore_parser.add_argument("--out", help="Write the run's findings as JSON to this path.")
    explore_parser.set_defaults(func=cmd_explore)

    diff_parser = subparsers.add_parser("diff", help="Diff findings between two exploration runs.")
    diff_parser.add_argument("run_a", help="Path to the earlier run's JSON output.")
    diff_parser.add_argument("run_b", help="Path to the later run's JSON output.")
    diff_parser.add_argument("--out", help="Write the diff report as Markdown to this path.")
    diff_parser.set_defaults(func=cmd_diff)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
