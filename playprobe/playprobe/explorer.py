"""Seeded heuristic exploration bot: random walk + rule-based anomaly detection.

The bot is deterministic (seeded RNG) and fully offline, not an LLM/ML agent —
it random-walks the build graph, then evaluates fixed rules over what it saw:
softlocks (dead ends), crashes (error states), balance outliers (statistically
extreme stat deltas), and exploit loops (cycles that grow a stat unbounded).
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .build import Build, Edge

MODIFIED_Z_THRESHOLD = 3.5
MIN_SAMPLES_FOR_OUTLIER = 3


@dataclass(frozen=True)
class Finding:
    kind: str  # "softlock" | "exploit_loop" | "balance_outlier" | "crash"
    fingerprint: str  # stable id used to match findings across runs
    summary: str
    details: Dict[str, object]

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "fingerprint": self.fingerprint,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class WalkResult:
    path: List[str]
    visited_nodes: Set[str]
    visited_edges: List[Edge]


@dataclass
class ExploreResult:
    build_name: str
    seed: int
    max_steps: int
    path_length: int
    visited_nodes: List[str]
    findings: List[Finding]

    def to_dict(self) -> dict:
        return {
            "build_name": self.build_name,
            "seed": self.seed,
            "max_steps": self.max_steps,
            "path_length": self.path_length,
            "visited_nodes": self.visited_nodes,
            "findings": [f.to_dict() for f in self.findings],
        }


def walk(build: Build, seed: int, max_steps: int) -> WalkResult:
    """Random-walk the build from its start node, restarting on dead ends."""
    rng = random.Random(seed)
    visited_nodes: Set[str] = {build.start}
    visited_edges: Dict[Tuple[str, str, str], Edge] = {}
    path: List[str] = [build.start]

    node = build.start
    for _ in range(max_steps):
        outgoing = build.outgoing_edges(node)
        if not outgoing:
            node = build.start
        else:
            edge = rng.choice(outgoing)
            visited_edges[(edge.from_node, edge.to_node, edge.action)] = edge
            node = edge.to_node
        visited_nodes.add(node)
        path.append(node)

    return WalkResult(path=path, visited_nodes=visited_nodes, visited_edges=list(visited_edges.values()))


def find_crashes(build: Build, visited_nodes: Set[str]) -> List[Finding]:
    findings = []
    for node_id in sorted(visited_nodes):
        if build.node_type(node_id) == "error":
            findings.append(
                Finding(
                    kind="crash",
                    fingerprint=f"crash:{node_id}",
                    summary=f"Reaching {node_id!r} puts the game in an unrecoverable error state",
                    details={"node": node_id},
                )
            )
    return findings


def find_softlocks(build: Build, visited_nodes: Set[str]) -> List[Finding]:
    findings = []
    for node_id in sorted(visited_nodes):
        if build.node_type(node_id) == "normal" and not build.outgoing_edges(node_id):
            findings.append(
                Finding(
                    kind="softlock",
                    fingerprint=f"softlock:{node_id}",
                    summary=f"{node_id!r} has no outgoing actions and is not a win state — the player gets stuck",
                    details={"node": node_id},
                )
            )
    return findings


def _modified_z_scores(values: List[float]) -> List[float]:
    """Robust outlier score (Iglesias & Hawkins) — resistant to the outlier itself skewing the baseline."""
    median = statistics.median(values)
    abs_devs = [abs(v - median) for v in values]
    mad = statistics.median(abs_devs)
    if mad == 0:
        # Most deltas are identical; any nonzero deviation is a clear outlier.
        return [MODIFIED_Z_THRESHOLD + 1 if d > 0 else 0.0 for d in abs_devs]
    return [0.6745 * (v - median) / mad for v in abs_devs]


def find_balance_outliers(build: Build, visited_edges: List[Edge]) -> List[Finding]:
    values_by_stat: Dict[str, List[float]] = {}
    for edge in visited_edges:
        for stat, delta in edge.stat_deltas.items():
            values_by_stat.setdefault(stat, []).append(delta)

    z_by_stat = {stat: _modified_z_scores(values) for stat, values in values_by_stat.items()}
    cursor = {stat: 0 for stat in values_by_stat}

    findings = []
    seen = set()
    for edge in visited_edges:
        for stat, delta in edge.stat_deltas.items():
            idx = cursor[stat]
            cursor[stat] += 1
            if len(values_by_stat[stat]) < MIN_SAMPLES_FOR_OUTLIER:
                continue
            z = z_by_stat[stat][idx]
            if abs(z) <= MODIFIED_Z_THRESHOLD:
                continue
            fingerprint = f"balance_outlier:{edge.from_node}->{edge.to_node}:{edge.action}:{stat}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            findings.append(
                Finding(
                    kind="balance_outlier",
                    fingerprint=fingerprint,
                    summary=(
                        f"{edge.action!r} ({edge.from_node} -> {edge.to_node}) changes {stat} by "
                        f"{delta:g}, a statistical outlier vs. the build's other {stat} deltas"
                    ),
                    details={"from": edge.from_node, "to": edge.to_node, "action": edge.action, "stat": stat, "delta": delta},
                )
            )
    return findings


def find_exploit_loops(build: Build, visited_edges: List[Edge]) -> List[Finding]:
    """Flag cycles (over edges the bot actually traversed) that grow a stat unbounded."""
    adjacency: Dict[str, List[Edge]] = {}
    for edge in visited_edges:
        adjacency.setdefault(edge.from_node, []).append(edge)

    findings: List[Finding] = []
    seen = set()
    stack: List[str] = []
    stack_edges: List[Edge] = []
    on_stack: Set[str] = set()
    globally_visited: Set[str] = set()

    def record_cycle(cycle_nodes: List[str], cycle_edges: List[Edge]) -> None:
        stat_sums: Dict[str, float] = {}
        for cycle_edge in cycle_edges:
            for stat, delta in cycle_edge.stat_deltas.items():
                stat_sums[stat] = stat_sums.get(stat, 0) + delta
        for stat, total in stat_sums.items():
            if total <= 0:
                continue
            key = ",".join(sorted(set(cycle_nodes)))
            fingerprint = f"exploit_loop:{key}:{stat}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            findings.append(
                Finding(
                    kind="exploit_loop",
                    fingerprint=fingerprint,
                    summary=(
                        f"Repeating {' -> '.join(cycle_nodes + [cycle_nodes[0]])} increases {stat} by "
                        f"{total:g} per loop with no bound"
                    ),
                    details={"cycle": list(cycle_nodes), "stat": stat, "delta_per_loop": total},
                )
            )

    def visit(node: str) -> None:
        stack.append(node)
        on_stack.add(node)
        for edge in adjacency.get(node, []):
            nxt = edge.to_node
            if nxt in on_stack:
                start = stack.index(nxt)
                record_cycle(stack[start:], stack_edges[start:] + [edge])
                continue
            stack_edges.append(edge)
            if nxt not in globally_visited:
                globally_visited.add(nxt)
                visit(nxt)
            stack_edges.pop()
        stack.pop()
        on_stack.discard(node)

    for node in list(adjacency.keys()):
        if node not in globally_visited:
            globally_visited.add(node)
            visit(node)

    return findings


def explore(build: Build, seed: int, max_steps: int = 500) -> ExploreResult:
    result = walk(build, seed, max_steps)
    findings: List[Finding] = []
    findings += find_crashes(build, result.visited_nodes)
    findings += find_softlocks(build, result.visited_nodes)
    findings += find_balance_outliers(build, result.visited_edges)
    findings += find_exploit_loops(build, result.visited_edges)
    return ExploreResult(
        build_name=build.name,
        seed=seed,
        max_steps=max_steps,
        path_length=len(result.path),
        visited_nodes=sorted(result.visited_nodes),
        findings=findings,
    )
