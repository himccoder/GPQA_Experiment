#!/usr/bin/env bash
# Run the three independent 198-question trials, then aggregate.
#
# Trials are sequential on purpose: they share one DeepSeek rate limit, and a
# failure in trial 2 should not be entangled with trial 3.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for trial in 1 2 3; do
  echo "=== Trial $trial / 3 ==="
  "$REPO_ROOT/scripts/run_trial.sh" "trial-$trial"
done

python3 "$REPO_ROOT/scripts/calculate_results.py"
