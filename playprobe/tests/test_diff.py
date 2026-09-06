import unittest

from playprobe.diff import diff_findings


def _finding(fingerprint, kind="softlock"):
    return {"kind": kind, "fingerprint": fingerprint, "summary": fingerprint, "details": {}}


class DiffTest(unittest.TestCase):
    def test_buckets_new_resolved_persisting(self):
        run_a = {
            "findings": [
                _finding("softlock:swamp"),
                _finding("balance_outlier:cave->boss_room:descend:hp", kind="balance_outlier"),
            ]
        }
        run_b = {
            "findings": [
                _finding("balance_outlier:cave->boss_room:descend:hp", kind="balance_outlier"),
                _finding("exploit_loop:cave,farm:gold", kind="exploit_loop"),
            ]
        }

        diff = diff_findings(run_a, run_b)

        self.assertEqual([f["fingerprint"] for f in diff["resolved"]], ["softlock:swamp"])
        self.assertEqual([f["fingerprint"] for f in diff["new"]], ["exploit_loop:cave,farm:gold"])
        self.assertEqual(
            [f["fingerprint"] for f in diff["persisting"]],
            ["balance_outlier:cave->boss_room:descend:hp"],
        )

    def test_no_overlap_is_all_new_and_resolved(self):
        run_a = {"findings": [_finding("softlock:a")]}
        run_b = {"findings": [_finding("softlock:b")]}

        diff = diff_findings(run_a, run_b)

        self.assertEqual([f["fingerprint"] for f in diff["new"]], ["softlock:b"])
        self.assertEqual([f["fingerprint"] for f in diff["resolved"]], ["softlock:a"])
        self.assertEqual(diff["persisting"], [])


if __name__ == "__main__":
    unittest.main()
