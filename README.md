# DeepSeek-V4-Flash-0731 on GPQA Diamond — Harbor + Terminus-2 replication

An attempt to reproduce Artificial Analysis's **~91%** GPQA Diamond result for
**DeepSeek-V4-Flash-0731**, run as an *agentic* evaluation: the model is driven
by **Terminus-2** inside a sandboxed Docker container by the **Harbor**
evaluation framework, over all **198** GPQA Diamond questions, **3 times**. The
reported number is the mean of the three trial accuracies. Target: **≥85%**.

This is a replication *under a specific harness*, not a re-measurement of AA's
setup. See [docs/experiment-notes.md](docs/experiment-notes.md) for why the two
numbers are not directly comparable.

## Architecture

```
GPQA Diamond CSV (198 gated questions, Hugging Face)
   │  scripts/build_tasks.py  → validate, then hand rows to Harbor's adapter
   ▼
Harbor task dirs (instruction.md + Dockerfile + tests/test.sh + solution/)
   │  harbor jobs start
   ▼
Terminus-2 ── tmux ──► Ubuntu container, writes its answer to /app/answer.txt
   │  LiteLLM  deepseek/deepseek-v4-flash
   ▼
DeepSeek API (https://api.deepseek.com) → DeepSeek-V4-Flash-0731
   │
   ▼
Harbor verifier (tests/test.sh) → reward 1 / 0 → result.json + trajectory.json
```

Harbor's `gpqa-diamond` adapter, its verifier and Terminus-2 are used
**unmodified**. This repo contributes the frozen configuration, the CSV
loader/validator, the trial scripts and the aggregation.

## Requirements

- Python 3.9+ (for the two scripts here; Harbor itself needs 3.12, installed by `uv`)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Docker, running
- `git`
- A Hugging Face account with access to the gated `Idavidrein/gpqa` dataset
- A DeepSeek API key

## Setup

```bash
# 1. Install the pinned Harbor checkout (clones ./harbor, runs uv sync)
./scripts/setup.sh

# 2. Credentials
cp .env.example .env      # fill in DEEPSEEK_API_KEY and HF_TOKEN
set -a && source .env && set +a

# 3. Build the 198 tasks (downloads + validates the gated CSV)
python3 scripts/build_tasks.py
```

`build_tasks.py` fails loudly unless it finds exactly 198 questions, all
required columns, four distinct non-empty choices per question, and no
duplicates. It prints the ground-truth letter distribution as a shuffle check.

### Authentication

Two separate credentials, both read from the environment, never from a file in
this repo:

- `HF_TOKEN` — used once by `scripts/build_tasks.py` to fetch the gated CSV.
  Accept the terms at <https://huggingface.co/datasets/Idavidrein/gpqa> first.
- `DEEPSEEK_API_KEY` — passed to the Terminus-2 agent via the `${DEEPSEEK_API_KEY}`
  template in `config/terminus2-deepseek.yaml`. Harbor resolves it from the host
  environment at launch and templatises it back out when it writes `config.json`,
  so the key never lands in the committed job output.

## Verify the harness before spending credits

```bash
# Oracle run: the reference solution writes the correct letter. This calls no
# model — it proves the dataset, task generation and verifier are sound.
# Expect 198/198.
uv run --project harbor harbor jobs start \
  -p datasets/gpqa-diamond -a oracle -o trajectories --job-name oracle-check --yes
python3 scripts/calculate_results.py oracle-check
```

Then scale up on the real model, checking the trajectory after each step:

```bash
./scripts/run_trial.sh smoke-1   -l 1     # one question, end to end
./scripts/run_trial.sh smoke-5   -l 5
./scripts/run_trial.sh smoke-10  -l 10
./scripts/run_trial.sh smoke-20  -l 20
```

Inspect a trajectory with `cat trajectories/smoke-1/*/agent/trajectory.json`, or
replay the terminal with `asciinema play trajectories/smoke-1/*/agent/recording.cast`.

## Pre-flight checklist

Everything below should be green before trial 1 starts. After that the
configuration is frozen: changing a model parameter mid-experiment makes it a
different experiment, and it must be documented and re-run from trial 1.

- [ ] `docker info` succeeds
- [ ] `./scripts/setup.sh` completed; `harbor --version` prints
- [ ] `HF_TOKEN` and `DEEPSEEK_API_KEY` exported
- [ ] `scripts/build_tasks.py` reported 198 validated questions
- [ ] `datasets/gpqa-diamond/` contains 198 task directories
- [ ] oracle run scores 198/198
- [ ] 1-question run: answer written, verifier scored it, `agent/trajectory.json` exists
- [ ] 5-, 10-, 20-question runs clean, no infrastructure errors
- [ ] cost of the 20-question run extrapolated to 594 trials and accepted
- [ ] `git status` clean; no dataset, key or `.env` staged

## Running the experiment

```bash
./scripts/run_trial.sh trial-1        # one trial: 198 questions
./scripts/run_all_trials.sh           # all three, then aggregate
```

If a trial dies partway through, resume it rather than restarting — Harbor keeps
the completed trials:

```bash
uv run --project harbor harbor jobs resume trajectories/trial-2
```

Aggregate at any time:

```bash
python3 scripts/calculate_results.py
```

## Results

> Not yet run — the experiment is pending a DeepSeek API key. Fill this table
> from `results/summary.json` after `./scripts/run_all_trials.sh`.

| Trial    | Correct | Total | Accuracy | Errors |
| -------- | ------: | ----: | -------: | -----: |
| 1        |       — |   198 |        — |      — |
| 2        |       — |   198 |        — |      — |
| 3        |       — |   198 |        — |      — |
| **Mean** |       — |     — |    **—** |      — |

```
Artificial Analysis: ~91%
Target:              ≥85%
This experiment:     —
```

## Repository layout

```
config/terminus2-deepseek.yaml   Frozen Harbor job config (the experiment definition)
scripts/setup.sh                 Clone + pin Harbor, install deps
scripts/build_tasks.py           Fetch/validate the GPQA CSV → 198 Harbor tasks
scripts/run_trial.sh             Run one job (a trial, or a smoke test with -l N)
scripts/run_all_trials.sh        The three trials, then aggregation
scripts/calculate_results.py     Harbor results → results/*.json + the table above
trajectories/trial-N/            Harbor's native job output (the deliverable)
results/                         Per-trial and summary JSON
docs/experiment-notes.md         Every non-default choice, with its reason
```

Each trial directory holds one subdirectory per question, named
`<task-id>__<short-uuid>`:

```
trajectories/trial-1/<task>__<uuid>/
├── config.json          # resolved trial config (secrets templatised)
├── result.json          # verdict: verifier_result.rewards.reward = 1 | 0
├── agent/
│   ├── trajectory.json  # the full Terminus-2 trajectory
│   └── recording.cast   # asciinema recording of the terminal session
└── verifier/
    ├── reward.txt
    └── test-stdout.txt  # shows expected vs. submitted letter
```

## Reproducibility

| | |
| --- | --- |
| Model | DeepSeek-V4-Flash-0731, called as `deepseek/deepseek-v4-flash` |
| Endpoint | `https://api.deepseek.com` (LiteLLM `deepseek` provider) |
| Benchmark | GPQA Diamond, 198 questions, `Idavidrein/gpqa` → `gpqa_diamond.csv` |
| Agent | Harbor Terminus-2 |
| Framework | Harbor, pinned at `71c39eafbd134d43ae3f489b5e6488b2a157de65` |
| Adapter | Harbor `adapters/gpqa-diamond`, unmodified |
| Choice-shuffle seed | 42 (adapter default) |
| Temperature | unset — DeepSeek's thinking-mode default |
| Reasoning | `reasoning_effort: high` |
| Max turns | 30 |
| Attempts / trial | 1 |
| Trials | 3 |
| Sampling seed | none — the DeepSeek API exposes no seed parameter |
| Date | to be recorded at run time |

Harbor writes the fully resolved configuration to
`trajectories/<trial>/config.json` on every run, so the table above can always
be checked against what actually executed.

## Data handling

`datasets/` and `.cache/` are gitignored: GPQA is gated and its questions must
not be redistributed. **Trajectories necessarily contain the question text**, so
if you publish this repository, keep it private or strip `trajectories/` first.
Generated tasks carry the GPQA canary string so leaked copies stay detectable.

## Licence and citation

GPQA is CC-BY-4.0. Cite the benchmark:

```bibtex
@inproceedings{rein2024gpqa,
  title={GPQA: A Graduate-Level Google-Proof Q\&A Benchmark},
  author={Rein, David and Hou, Betty Li and Stickland, Asa Cooper and Petty, Jackson
          and Pang, Richard Yuanzhe and Dirani, Julien and Michael, Julian and Bowman, Samuel R},
  booktitle={First Conference on Language Modeling},
  year={2024}
}
```
