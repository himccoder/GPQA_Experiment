#!/usr/bin/env python3
"""Aggregate Harbor trial jobs into per-trial and summary results.

Reads Harbor's native per-trial `result.json` files under trajectories/<job>/
and writes results/<job>.json plus results/summary.json.

A question counts as correct when the Harbor verifier awarded reward == 1.
Trials that never reached the verifier (API outage, Docker failure, timeout)
are counted as `errors`, never as wrong answers — but they still count against
the 198-question denominator, so accuracy is never inflated by dropping them.

Usage:
    python3 scripts/calculate_results.py                 # trial-1, trial-2, trial-3
    python3 scripts/calculate_results.py smoke-1         # any job name(s)
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAJECTORIES_DIR = REPO_ROOT / "trajectories"
RESULTS_DIR = REPO_ROOT / "results"
TOTAL_QUESTIONS = 198


def summarize_job(job_dir: Path) -> dict:
    """Turn one Harbor job directory into a result summary."""
    questions, errors = [], []
    tokens_in = tokens_out = 0
    cost_usd = 0.0

    for result_path in sorted(job_dir.glob("*/result.json")):
        result = json.loads(result_path.read_text())

        agent = result.get("agent_result") or {}
        tokens_in += agent.get("n_input_tokens") or 0
        tokens_out += agent.get("n_output_tokens") or 0
        cost_usd += agent.get("cost_usd") or 0.0

        verifier = result.get("verifier_result") or {}
        reward = (verifier.get("rewards") or {}).get("reward")
        exception = result.get("exception_info")

        if reward is None:
            errors.append(
                {
                    "task_name": result["task_name"],
                    "trial_dir": result_path.parent.name,
                    "error": (exception or {}).get("exception_type", "no reward"),
                    "message": (exception or {}).get("exception_message", "")[:300],
                }
            )
        questions.append({"task_name": result["task_name"], "reward": reward})

    correct = sum(1 for q in questions if q["reward"] == 1)
    return {
        "trial": job_dir.name,
        "correct": correct,
        "total": TOTAL_QUESTIONS,
        "n_completed": len(questions) - len(errors),
        "n_errors": len(errors),
        "accuracy": round(correct / TOTAL_QUESTIONS, 4),
        "n_input_tokens": tokens_in,
        "n_output_tokens": tokens_out,
        "cost_usd": round(cost_usd, 4),
        "errors": errors,
        # Task names are numeric strings ("0".."197"); sort them numerically.
        "questions": sorted(questions, key=lambda q: int(q["task_name"])),
    }


def main() -> None:
    job_names = sys.argv[1:] or ["trial-1", "trial-2", "trial-3"]
    RESULTS_DIR.mkdir(exist_ok=True)

    trials = []
    for name in job_names:
        job_dir = TRAJECTORIES_DIR / name
        if not job_dir.is_dir():
            sys.exit(f"No such job directory: {job_dir}")
        summary = summarize_job(job_dir)
        (RESULTS_DIR / f"{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
        trials.append(summary)

    # The reported number is the mean of the per-trial accuracies, not the
    # accuracy of all answers pooled together (they coincide only when every
    # trial has the same denominator, which is the case here).
    mean_accuracy = sum(t["accuracy"] for t in trials) / len(trials)
    summary = {
        "benchmark": "GPQA-Diamond",
        "num_questions": TOTAL_QUESTIONS,
        "num_trials": len(trials),
        "model": "DeepSeek-V4-Flash-0731 (deepseek/deepseek-v4-flash)",
        "agent": "Terminus-2",
        "framework": "Harbor",
        "trials": [
            {k: t[k] for k in ("trial", "correct", "total", "n_errors", "accuracy",
                               "n_input_tokens", "n_output_tokens", "cost_usd")}
            for t in trials
        ],
        "mean_accuracy": round(mean_accuracy, 4),
        "total_cost_usd": round(sum(t["cost_usd"] for t in trials), 4),
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("| Trial | Correct | Total | Accuracy | Errors |")
    print("| ----- | ------: | ----: | -------: | -----: |")
    for t in trials:
        print(f"| {t['trial']} | {t['correct']} | {t['total']} | "
              f"{t['accuracy'] * 100:.2f}% | {t['n_errors']} |")
    print(f"| **Mean** | — | — | **{mean_accuracy * 100:.2f}%** | — |")
    print(f"\nTotal cost: ${summary['total_cost_usd']:.2f}")
    print(f"Wrote {RESULTS_DIR}/summary.json")


if __name__ == "__main__":
    main()
