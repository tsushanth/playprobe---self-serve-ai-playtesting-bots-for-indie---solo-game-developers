"""Render exploration findings and diffs as console text or Markdown."""
from __future__ import annotations

from typing import Dict, List

_DIFF_SECTIONS = (("New", "new"), ("Resolved", "resolved"), ("Persisting", "persisting"))


def render_explore_console(result: dict) -> str:
    lines = [
        f"PlayProbe explore: {result['build_name']} (seed={result['seed']}, steps={result['max_steps']})",
        f"Visited {len(result['visited_nodes'])} node(s).",
        "",
    ]
    findings = result["findings"]
    if not findings:
        lines.append("No issues found.")
    else:
        lines.append(f"Found {len(findings)} issue(s):")
        for finding in findings:
            lines.append(f"  [{finding['kind']}] {finding['summary']}")
    return "\n".join(lines) + "\n"


def render_diff_console(diff: Dict[str, List[dict]]) -> str:
    lines = ["PlayProbe diff report", ""]
    for label, key in _DIFF_SECTIONS:
        items = diff[key]
        lines.append(f"{label} ({len(items)}):")
        if not items:
            lines.append("  (none)")
        for finding in items:
            lines.append(f"  [{finding['kind']}] {finding['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_diff_markdown(diff: Dict[str, List[dict]], run_a_name: str, run_b_name: str) -> str:
    lines = [f"# PlayProbe diff: {run_a_name} -> {run_b_name}", ""]
    for label, key in _DIFF_SECTIONS:
        items = diff[key]
        lines.append(f"## {label} ({len(items)})")
        if not items:
            lines.append("- (none)")
        for finding in items:
            lines.append(f"- **[{finding['kind']}]** {finding['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
