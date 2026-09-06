"""Load and validate a PlayProbe build graph.

A "build" is a portable stand-in for a game level: nodes are game states
(typed normal / win / error), edges are player actions with stat deltas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List

VALID_NODE_TYPES = {"normal", "win", "error"}


@dataclass(frozen=True)
class Edge:
    from_node: str
    to_node: str
    action: str
    stat_deltas: Dict[str, float]


@dataclass
class Build:
    name: str
    start: str
    node_types: Dict[str, str]
    edges: List[Edge]
    _outgoing: Dict[str, List[Edge]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        outgoing: Dict[str, List[Edge]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge.from_node, []).append(edge)
        self._outgoing = outgoing

    def node_type(self, node_id: str) -> str:
        return self.node_types[node_id]

    def outgoing_edges(self, node_id: str) -> List[Edge]:
        return self._outgoing.get(node_id, [])


def load_build(path: str) -> Build:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return build_from_dict(raw)


def build_from_dict(raw: dict) -> Build:
    name = raw["name"]
    start = raw["start"]
    nodes = raw["nodes"]

    node_types: Dict[str, str] = {}
    for node_id, node in nodes.items():
        node_type = node.get("type", "normal")
        if node_type not in VALID_NODE_TYPES:
            raise ValueError(f"node {node_id!r} has invalid type {node_type!r}")
        node_types[node_id] = node_type

    if start not in node_types:
        raise ValueError(f"start node {start!r} is not defined in nodes")

    edges: List[Edge] = []
    for raw_edge in raw.get("edges", []):
        from_node = raw_edge["from"]
        to_node = raw_edge["to"]
        if from_node not in node_types:
            raise ValueError(f"edge references unknown from-node {from_node!r}")
        if to_node not in node_types:
            raise ValueError(f"edge references unknown to-node {to_node!r}")
        edges.append(
            Edge(
                from_node=from_node,
                to_node=to_node,
                action=raw_edge["action"],
                stat_deltas=dict(raw_edge.get("stat_deltas", {})),
            )
        )

    return Build(name=name, start=start, node_types=node_types, edges=edges)
