# PlayProbe — Local MVP Scaffold Plan

Goal: prove the core value — a bot explores a game build, auto-discovers bugs/softlocks/exploits/balance outliers, and produces a nightly diff against a previous build — as a local CLI. No product, no deployment, no plugin.

## 1. Stack

**Plain Python 3, standard library only.** No pip dependencies, no build step, no package manager beyond what ships with Python.

Why this over Node/TS or Go:
- Python's stdlib (`json`, `random`, `statistics`, `argparse`, `unittest`) covers everything needed: graph traversal, seeded randomness, outlier detection, CLI parsing, and tests — with zero installs.
- A single `python3 playprobe/cli.py explore ...` run is the fastest possible path from clone to "seeing it work," which is the point of this scaffold.
- Node/TS would need `npm install` + tsconfig for no added benefit here; Go would need a compile step and offers no library advantage for this graph/stats workload.

## 2. The key scoping decision: simulate the "build," don't integrate an engine

The real product plugs into Unity/Godot and explores an actual running game. Standing that up (an editor plugin, a live game process, pixel/input-level control) is a separate, much larger engineering effort and isn't needed to demonstrate the *bug-discovery-and-diff* value.

Instead, a "build" is represented as a portable **state graph JSON file**: nodes are game states (with a type — normal / win / error — and stat effects), edges are player actions (with stat deltas). This is a stand-in for "a level with mechanics," small enough to hand-author two versions of (baseline + "tonight's build") with deliberately seeded bugs. The exploration/diff logic this scaffold proves would plug into a real engine adapter later; that adapter is explicitly not built here.

Similarly, "AI exploration bot" here means a **deterministic, seeded heuristic explorer** (random walk + rule-based anomaly detection over the graph), not an LLM- or ML-driven agent. Real AI-driven exploration would need model API calls/network access and wouldn't be reproducible run-to-run, which would undermine testing the diff logic. The heuristic explorer proves the workflow (explore → flag issues → diff builds) cheaply, deterministically, and fully offline.

## 3. Explicitly out of scope

- No Unity/Godot plugin or engine integration of any kind.
- No auth, accounts, or multi-user anything.
- No billing/Stripe/credit-card signup.
- No hosting, deployment, or server process — pure local files and a CLI.
- No web dashboard/UI — console output plus JSON/Markdown report files.
- No real scheduler/cron for "nightly" runs — nightliness is demonstrated by manually running `diff` against two build files representing consecutive nights.
- No database — findings and diffs are plain JSON/Markdown on disk.
- No pixel/vision-based or live-input exploration — traversal is over the abstract state graph.
- No actual LLM/ML calls — see heuristic-explorer rationale above.

None of these are needed to demonstrate: bot explores a build → finds issues → same bot explores a changed build → diff shows new/fixed/persisting issues.

## 4. File/directory layout

```
playprobe/
  playprobe/
    __init__.py
    build.py         # load + validate a build graph JSON
    explorer.py       # seeded heuristic bot: traversal + issue detection
                       #   (softlock, exploit loop, balance outlier, error/crash state)
    diff.py           # fingerprint-match findings across two runs;
                       #   categorize new / resolved / persisting
    report.py         # render findings/diff as console text + Markdown
    cli.py            # argparse entrypoint: `explore` and `diff` subcommands
  samples/
    build_a.json       # baseline build, 3 seeded issues
    build_b.json       # "nightly" build: 1 fixed, 1 new, 1 persisting issue
  tests/
    test_explorer.py    # unit tests for each issue-detection rule
    test_diff.py         # unit tests for new/resolved/persisting categorization
    fixtures/
      tiny_build.json    # minimal hand-crafted graph for fast, exact assertions
  README.md              # quickstart: exact commands to run the demo
```

No `pyproject.toml`/packaging metadata needed for a local demo — `python3 -m playprobe.cli ...` run from the repo root is sufficient.

## 5. Verification

**Unit tests** (`python3 -m unittest discover tests`, stdlib `unittest`, no test framework dependency):
- `test_explorer.py`: given small fixture graphs, assert each detection rule fires correctly in isolation — a dead-end non-win node is flagged as a softlock; a cycle with monotonically increasing stat is flagged as an exploit; an edge with a stat delta far outside the graph's mean is flagged as a balance outlier; an `error`-typed node is flagged as a crash.
- `test_diff.py`: given two canned finding lists, assert correct bucketing into new/resolved/persisting.

**Manual run-through** (the end-to-end demo):
```
python3 -m playprobe.cli explore samples/build_a.json --seed 1 --out run_a.json
python3 -m playprobe.cli explore samples/build_b.json --seed 1 --out run_b.json
python3 -m playprobe.cli diff run_a.json run_b.json
```
Expected, eyeballable output: the diff report lists exactly the seeded deltas between `build_a.json` and `build_b.json` (one resolved softlock, one new exploit loop, one persisting balance outlier), confirming the explore→detect→diff pipeline works end to end on nothing but local files.
