# PlayProbe — Local MVP Scaffold

A local, offline proof of the core PlayProbe value: a bot explores a game
build, auto-discovers bugs, and produces a nightly diff against the previous
build. This is **not** the real product (no Unity/Godot plugin, no billing,
no server) — see `plan.md` in the repo root for what's deliberately out of
scope and why.

## What this proves

`explore` → bot walks a build, flags issues → same bot explores a changed
build → `diff` shows which issues are new, resolved, or still there. That
loop is the entire pitch; everything else (engine integration, hosting,
payments) is packaging around it.

## How a "build" is represented

Instead of a real running game, a build is a JSON **state graph**: nodes are
game states (`normal`, `win`, or `error`), edges are player actions carrying
stat deltas (e.g. `hp: -60`). See `samples/build_a.json` for the format.

The bot itself is a **deterministic, seeded heuristic explorer** — a
random walk over the graph plus fixed detection rules — not an LLM or ML
model. That keeps every run reproducible and fully offline, which is what
lets `diff` mean anything.

It flags four kinds of issues:
- **softlock** — a normal (non-win) node with no outgoing actions: the player gets stuck.
- **crash** — an `error`-typed node is reached.
- **balance outlier** — an action's stat delta is a statistical outlier compared to the build's other deltas for that stat.
- **exploit loop** — a cycle of actions that increases some stat with no bound (infinite farming).

## Requirements

Python 3.9+, standard library only. No installs.

## Quickstart

Run from this directory (`playprobe/`):

```bash
python3 -m playprobe.cli explore samples/build_a.json --seed 1 --out run_a.json
python3 -m playprobe.cli explore samples/build_b.json --seed 1 --out run_b.json
python3 -m playprobe.cli diff run_a.json run_b.json
```

Expected output: the diff report shows exactly one resolved softlock, one
new exploit loop, and one persisting balance outlier — the seeded deltas
between `build_a.json` (night 1) and `build_b.json` (night 2).

Pass `--out report.md` to `diff` to also write the same report as Markdown.

## Running the tests

```bash
python3 -m unittest discover tests
```

`tests/test_explorer.py` exercises each detection rule directly against a
tiny hand-crafted fixture graph (`tests/fixtures/tiny_build.json`) so
assertions are exact rather than dependent on random-walk luck.
`tests/test_diff.py` checks the new/resolved/persisting bucketing logic.

## Layout

```
playprobe/
  build.py      # load + validate a build graph JSON
  explorer.py   # seeded heuristic bot: random walk + issue-detection rules
  diff.py       # fingerprint-match findings across two runs
  report.py     # render findings/diff as console text or Markdown
  cli.py        # `explore` and `diff` subcommands
samples/
  build_a.json  # baseline build
  build_b.json  # "nightly" build with one fixed, one new, one persisting issue
tests/
```
