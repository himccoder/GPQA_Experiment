#!/usr/bin/env bash
# Run one Harbor job over the generated GPQA-Diamond tasks.
#
#   scripts/run_trial.sh trial-1              # all 198 questions
#   scripts/run_trial.sh smoke-1 -l 1         # first question only  (-l = --n-tasks)
#   scripts/run_trial.sh smoke-10 -l 10
#
# Any extra arguments are passed straight through to `harbor jobs start` and
# override the frozen config, so keep them to test runs only.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARBOR_ROOT="${HARBOR_ROOT:-$REPO_ROOT/harbor}"

JOB_NAME="${1:?usage: run_trial.sh <job-name> [harbor args...]}"
shift

if [ ! -d "$REPO_ROOT/datasets/gpqa-diamond" ]; then
  echo "Tasks not built. Run: python3 scripts/build_tasks.py" >&2
  exit 1
fi

if [ -e "$REPO_ROOT/trajectories/$JOB_NAME" ]; then
  echo "trajectories/$JOB_NAME already exists. Pick another name, or resume it:" >&2
  echo "  uv run --project $HARBOR_ROOT harbor jobs resume trajectories/$JOB_NAME" >&2
  exit 1
fi

# cd to the repo root: the paths inside the config are resolved against $PWD.
cd "$REPO_ROOT"
uv run --project "$HARBOR_ROOT" harbor jobs start \
  --config config/terminus2-deepseek.yaml \
  --job-name "$JOB_NAME" \
  --yes \
  "$@"
