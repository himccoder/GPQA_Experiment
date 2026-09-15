#!/usr/bin/env bash
# Runs the three trials, then aggregates.
#
# Safe to re-run: a trial whose directory already exists is skipped, so an
# interrupted experiment continues where it stopped.
#
# Two guards, both learned the hard way during this experiment:
#   - waits for the Docker daemon, which died mid-run once;
#   - stops before a trial if the DeepSeek balance cannot cover it, because a
#     trial that runs out of funds produces 198 infrastructure errors, not a
#     result.
#
# Run it under caffeinate so the machine does not idle-sleep:
#   caffeinate -dimsu ./scripts/run_all_trials.sh      # logs to logs/run-<timestamp>.log
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.local/bin:$PATH"
set -a && source .env && set +a

mkdir -p logs
LOG="logs/run-$(date '+%Y%m%d-%H%M%S').log"
MIN_BALANCE=8.0   # a trial cost $7.3-$8.4 in this experiment

balance() {
  curl -s --max-time 30 https://api.deepseek.com/user/balance \
    -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['balance_infos'][0]['total_balance'])" 2>/dev/null
}

{
  echo "=== started $(date) ==="

  # Docker Desktop cannot be restarted from the shell once its backend has been
  # killed; it needs a GUI launch. Wait up to 60 min for someone to start it,
  # then give up rather than running 594 tasks against a dead daemon.
  waited=0
  until docker info >/dev/null 2>&1; do
    if [ $waited -ge 3600 ]; then
      echo "!!! ABORTING: Docker daemon still down after 60 min. Start Docker"
      echo "!!! Desktop, then re-run: ./scripts/run_all_trials.sh"
      exit 1
    fi
    [ $((waited % 300)) -eq 0 ] && echo "waiting for Docker daemon... (${waited}s)"
    sleep 15; waited=$((waited+15))
  done
  echo "Docker daemon up after ${waited}s"

  echo "config: $(grep -E '^n_concurrent_trials' config/terminus2-deepseek.yaml)"
  echo "balance at start: \$$(balance)"

  for trial in 1 2 3; do
    bal=$(balance)
    if [ -n "$bal" ] && [ "$(echo "$bal < $MIN_BALANCE" | bc -l 2>/dev/null)" = "1" ]; then
      echo "!!! ABORTING before trial $trial: balance \$$bal is below \$$MIN_BALANCE."
      echo "!!! Top up, then resume with: ./scripts/run_trial.sh trial-$trial"
      break
    fi

    if [ -e "trajectories/trial-$trial" ]; then
      echo "=== trial-$trial already exists, skipping (resume manually if incomplete) ==="
      continue
    fi

    echo "=== Trial $trial/3 started $(date '+%H:%M:%S') (balance \$$bal) ==="
    ./scripts/run_trial.sh "trial-$trial" 2>&1 \
      | grep -vE "LiteLLM:WARNING|reasoning_content|max_turns artificially"
    echo "=== Trial $trial/3 finished $(date '+%H:%M:%S') ==="
    echo "completed trajectories: $(ls trajectories/trial-$trial 2>/dev/null | grep -c '__')/198"
  done

  echo "=== aggregating ==="
  python3 scripts/calculate_results.py 2>&1 || echo "(aggregation needs all three trials)"
  echo "balance at end: \$$(balance)"
  echo "=== finished $(date) ==="
} 2>&1 | tee "$LOG"

echo "Log: $REPO_ROOT/$LOG"
