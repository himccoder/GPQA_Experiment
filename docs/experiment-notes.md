# Experiment notes

Design decisions, and the evidence behind them. Everything here was checked
against the pinned Harbor checkout and the live DeepSeek / Artificial Analysis
documentation rather than assumed.

## What is reused, and what is ours

| Component | Source |
| --- | --- |
| Question set, choice shuffling, task generation | Harbor `adapters/gpqa-diamond/adapter.py`, unmodified |
| Prompt / instruction text | Harbor `adapters/gpqa-diamond/template/instruction.md`, unmodified |
| Verifier (answer extraction + grading) | Harbor `adapters/gpqa-diamond/template/tests/test.sh`, unmodified |
| Oracle solution | Harbor `adapters/gpqa-diamond/template/solution/solve.sh`, unmodified |
| Agent | Harbor `terminus-2`, unmodified |
| Trajectory format | Harbor native (`agent/trajectory.json`, `agent/recording.cast`) |
| **Ours** | the job config, the CSV loader/validator, the trial scripts, the aggregation |

The only reason `scripts/build_tasks.py` exists instead of Harbor's
`adapters/gpqa-diamond/run_adapter.py` is the data source: `run_adapter.py`
calls `load_dataset("Idavidrein/gpqa", "gpqa_diamond")`, and we were asked to
use the canonical CSV at
`https://huggingface.co/datasets/Idavidrein/gpqa/resolve/main/gpqa_diamond.csv`.
Our script fetches and validates that CSV and then hands the rows straight to
Harbor's `GPQAAdapter`, so task ids, shuffling, prompts and grading are
identical to an upstream `run_adapter.py` run.

## The model

DeepSeek's API docs list three chat models: `deepseek-v4-flash`,
`deepseek-v4-pro`, `deepseek-v4-flash-vision-exp`. The docs state that
**`deepseek-v4-flash` has been updated to DeepSeek-V4-Flash-0731**, with the
calling method unchanged — so `deepseek-v4-flash` *is* the 0731 checkpoint and
there is no separate `-0731` API alias to call. The base URL is
`https://api.deepseek.com` (OpenAI-compatible).

Harbor already knows this provider: `src/harbor/agents/model_connection.py`
maps the `deepseek` prefix to `DEEPSEEK_API_KEY` + `https://api.deepseek.com`,
and LiteLLM's model table has `deepseek/deepseek-v4-flash` with a 1M-token
context, 393,216 max output tokens and correct per-token pricing. That means no
`api_base` override and no `model_info` override are needed — both are left
unset in the config, which is why you will not find them there.

## Configuration choices

| Parameter | Value | Why |
| --- | --- | --- |
| `model_name` | `deepseek/deepseek-v4-flash` | see above |
| `reasoning_effort` | `high` | DeepSeek's own docs use `reasoning_effort: "high"` in their reasoning examples; AA's 91% is a thinking-mode number |
| `temperature` | **unset** | Terminus-2 sends no `temperature` field when it is `None`, so DeepSeek's default for thinking mode applies. Pinning a temperature on a reasoning model is not a neutral choice — providers commonly ignore or reject it — so we record "provider default" rather than a number we cannot verify was honoured |
| `max_turns` | `30` | Harbor's default is effectively unlimited. Writing one letter to `/app/answer.txt` takes a handful of turns; 30 bounds a runaway agent without truncating a healthy trial |
| `parser_name` | `json` (default) | unchanged |
| `enable_summarize` | `true` (default) | never expected to fire: a GPQA trial is far below a 1M context |
| `n_attempts` | `1` | the three trials are three separate jobs, not `-k 3` within one |
| `max_retries` | `2` | retries infrastructure failures only. A wrong answer is a *completed* trial with reward 0 and is never retried, so this cannot inflate accuracy |
| `n_concurrent_trials` | `4` | throughput only; lower it if DeepSeek rate-limits you |
| seed | `42` | the Harbor adapter default for the choice shuffle |

### Determinism

DeepSeek's API exposes no seed parameter, so runs are not bit-reproducible.
This is exactly why the protocol calls for three trials and a mean.

## Accounting rules

- **Correct** = Harbor verifier reward `1` (the answer letter in
  `/app/answer.txt` matches ground truth after whitespace/case normalisation).
- **Incorrect** = reward `0`. This includes a missing or malformed answer file:
  the verifier treats "no valid letter" as wrong, which matches how AA scores
  an unparseable response.
- **Error** = the trial never produced a reward (API outage, Docker failure,
  agent crash). These are reported separately in `results/trial-N.json`, and
  they still count against the 198 denominator — dropping them would inflate
  accuracy.
- **Accuracy** = correct / 198 per trial; the headline number is the **mean of
  the three trial accuracies**, not all 594 answers pooled.

## Comparability with Artificial Analysis

AA reports ~91% for DeepSeek V4 Flash 0731 on GPQA Diamond. This replication is
not the same measurement, and the gap should not be read as a claim about the
model. Differences that are known up front:

1. **Agentic, not single-shot.** Terminus-2 drives a tmux session in a Docker
   container and must *write* its answer to `/app/answer.txt`. AA prompts the
   model directly.
2. **Shuffled choices.** Harbor's adapter re-shuffles A/B/C/D per question with
   a fixed seed; the original option ordering is not preserved.
3. **Extra instructions.** The task adds file-writing instructions to the
   question.

Harbor's own parity experiment quantifies this cost: on the same adapter,
`codex + gpt-5.2` scored **87.2%** where the original harness scored **87.9%**,
and OpenAI's direct-evaluation number for the same model was 92.4%. A ~1 point
harness penalty against a matched harness, and several points against direct
evaluation, is the expected shape of the difference.

## Data handling

`datasets/` and `.cache/` are gitignored — the GPQA questions are gated and
must not be redistributed. **The trajectories are different**: an agent
trajectory necessarily contains the question text it was reasoning about, so
`trajectories/` reproduces the benchmark. Publish this repository privately, or
strip the trajectories before making it public. Each generated task carries the
GPQA canary string (`t-bench-canary GUID 26b5c67b-...`) so leaked copies are
detectable in future training corpora.
