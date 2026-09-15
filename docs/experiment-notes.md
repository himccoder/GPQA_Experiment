# Experiment notes

Why each choice was made. Everything here was checked against the pinned Harbor
checkout and the live DeepSeek API, not assumed.

## What is reused, and what is ours

| Component | Source |
| --- | --- |
| Questions, choice shuffle, task generation | Harbor `adapters/gpqa-diamond/adapter.py`, unmodified |
| Prompt text | Harbor `template/instruction.md`, unmodified |
| Verifier (answer extraction + grading) | Harbor `template/tests/test.sh`, unmodified |
| Agent | Harbor `terminus-2`, unmodified |
| Trajectory format | Harbor native (`agent/trajectory.json`) |
| **Ours** | the job config, the CSV loader/validator, the run scripts, the aggregation |

`scripts/build_tasks.py` exists instead of Harbor's `run_adapter.py` only because of
the data source: `run_adapter.py` calls `load_dataset("Idavidrein/gpqa")`, and we were
asked to use the canonical CSV. Our script fetches and validates that CSV, then hands
the rows to Harbor's `GPQAAdapter`, so task ids, shuffling, prompts and grading are
identical to an upstream run.

## The model

The DeepSeek API lists two chat models: `deepseek-flash` and `deepseek-v4-pro`.
`deepseek-v4-flash` is not in that list but works as an alias — both resolve to the
same served model, confirmed by an identical `system_fingerprint`
(`aeb56401ca74e127821c4f9126dcb669`). We call it as `deepseek/deepseek-v4-flash`.

Harbor already maps the `deepseek` prefix to `https://api.deepseek.com` with
`DEEPSEEK_API_KEY`, and LiteLLM knows the model's pricing ($0.30/M input, $1.20/M
output), so no `api_base` or `model_info` override is needed.

The same fingerprint appears in all three trials, so the model did not change
mid-experiment.

## Configuration choices

| Parameter | Value | Why |
| --- | --- | --- |
| `reasoning_effort` | `high` | the reference number is a thinking-mode result |
| `temperature` | unset | Terminus-2 then sends no temperature field and DeepSeek's thinking-mode default applies. Pinning one on a reasoning model is not neutral — providers often ignore or reject it — so we record "provider default" rather than a number we cannot verify was honoured |
| `max_turns` | `30` | Harbor's default is effectively unlimited. Writing one letter takes a handful of turns; 30 bounds a runaway agent |
| `n_attempts` | `1` | the three trials are three separate jobs |
| `max_retries` | `2` | infrastructure failures only. A wrong answer is a *completed* trial with reward 0 and is never retried, so retries cannot inflate accuracy |
| `n_concurrent_trials` | `4` | throughput only. Raising it to 8 killed Docker Desktop's backend, so it stayed at 4 |
| seed | `42` | the Harbor adapter default for the choice shuffle |

DeepSeek exposes no seed parameter, so runs are not bit-reproducible. That is why the
protocol calls for three trials and a mean.

## Dataset notes

Validation requires 198 questions, four choices each, no duplicate questions, and the
correct answer distinct from its distractors in every row.

Rows 89 and 126 repeat one distractor verbatim, so those questions effectively offer
three distinct options. This is upstream GPQA data and was **left unmodified** —
rewriting choices would change the benchmark. The correct answer is still unique in
both rows, so the ground-truth letter is unambiguous.

## How answers are scored

- **Correct** = verifier reward `1`: the letter in `/app/answer.txt` matches ground
  truth after whitespace/case normalisation.
- **Incorrect** = reward `0`, including a missing or malformed answer file.
- **Error** = no reward at all (API outage, Docker failure, agent crash). These are
  reported separately and still count against the 198 denominator. There were **none**
  in any trial.
- **Accuracy** = correct / 198 per trial. The headline figure is the **mean of the
  three trial accuracies**, not all 594 answers pooled.

## Comparison with Artificial Analysis

AA runs GPQA Diamond by direct prompting — the model answers the multiple-choice
question and the letter is extracted with a regex, scored pass@1. This experiment is
agentic: Terminus-2 drives a tmux session in a Docker container and the model must
write its answer to a file. The extra instructions, the shuffled choices and the
file-writing step all make it a harder setting.

Harbor's own parity experiment gives a sense of the cost: on this adapter,
`codex + gpt-5.2` scored **87.2%** where the original harness scored **87.9%**.

Two further caveats:

- GPQA Diamond is now a legacy evaluation at AA, and no score for this model appeared
  on their live model page, so the ~91% could not be verified directly.
- The agent containers had internet access (Harbor's default). 32 of 594 tasks (5.4%)
  used a search engine and scored 37.5%, against 93.8% for the 562 that did not.
  Searching went with failure, not success. Scoring every searched task wrong gives a
  floor of 88.72%.

## Known issue: multi-turn reasoning replay

LiteLLM warns on every multi-turn call that the assistant message is missing
`reasoning_content`, and injects a placeholder. The model therefore sees a blank
reasoning chain for its own earlier turns. Reasoning is captured in full in the saved
trajectories, so this affects the agent's multi-turn fidelity, not the recorded data.

## Run record

| | |
| --- | --- |
| Harbor | 0.22.0, pinned at `71c39eafbd134d43ae3f489b5e6488b2a157de65` |
| Trials 1–2 | 2026-09-14, 00:33–05:05 CDT |
| Trial 3 | 2026-09-14, 17:37–19:57 CDT |
| Tokens | 28.4M input, 19.1M output |
| Cost | $23.84 |

Trial 3 was started once earlier and abandoned: DeepSeek's flash endpoint stalled —
requests opened but never returned — so every task timed out with zero tokens. Those
results were deleted and the trial was re-run cleanly once the endpoint recovered. No
tokens were billed for the stalled attempt.

## Data handling

`datasets/`, `.cache/` and `.env` are gitignored; GPQA is gated and must not be
redistributed. The trajectories necessarily contain the question text, so this
repository should stay private. Generated tasks carry the GPQA canary string.
