"""Fingerprint-match findings across two exploration runs.

Categorizes findings into new / resolved / persisting so a "nightly" run can
be diffed against the previous night's run.
"""
from __future__ import annotations

import json
from typing import Dict, List


def load_run(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_findings(run_a: dict, run_b: dict) -> Dict[str, List[dict]]:
    findings_a = {f["fingerprint"]: f for f in run_a["findings"]}
    findings_b = {f["fingerprint"]: f for f in run_b["findings"]}

    new = [findings_b[fp] for fp in findings_b if fp not in findings_a]
    resolved = [findings_a[fp] for fp in findings_a if fp not in findings_b]
    persisting = [findings_b[fp] for fp in findings_b if fp in findings_a]

    def sort_key(finding: dict) -> str:
        return finding["fingerprint"]

    return {
        "new": sorted(new, key=sort_key),
        "resolved": sorted(resolved, key=sort_key),
        "persisting": sorted(persisting, key=sort_key),
    }
