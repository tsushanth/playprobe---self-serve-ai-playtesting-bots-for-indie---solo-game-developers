import os
import unittest

from playprobe import explorer
from playprobe.build import load_build

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tiny_build.json")


class ExplorerRulesTest(unittest.TestCase):
    """Each rule is exercised directly against a hand-crafted fixture graph,
    bypassing the random walk so assertions are exact, not seed-dependent."""

    def setUp(self):
        self.build = load_build(FIXTURE)
        self.all_nodes = set(self.build.node_types.keys())
        self.all_edges = list(self.build.edges)

    def test_softlock_flags_dead_end_non_win_node(self):
        findings = explorer.find_softlocks(self.build, self.all_nodes)
        fingerprints = {f.fingerprint for f in findings}
        self.assertEqual(fingerprints, {"softlock:c"})

    def test_crash_flags_error_typed_node(self):
        findings = explorer.find_crashes(self.build, self.all_nodes)
        fingerprints = {f.fingerprint for f in findings}
        self.assertEqual(fingerprints, {"crash:d"})

    def test_balance_outlier_flags_extreme_delta(self):
        findings = explorer.find_balance_outliers(self.build, self.all_edges)
        fingerprints = {f.fingerprint for f in findings}
        self.assertEqual(fingerprints, {"balance_outlier:a->d:go_d:score"})

    def test_exploit_loop_flags_monotonically_increasing_cycle(self):
        findings = explorer.find_exploit_loops(self.build, self.all_edges)
        fingerprints = {f.fingerprint for f in findings}
        self.assertEqual(fingerprints, {"exploit_loop:a,b:score"})


if __name__ == "__main__":
    unittest.main()
