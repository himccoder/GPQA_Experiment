#!/usr/bin/env bash
# Installs the pinned Harbor checkout that this experiment runs on.
#
# Harbor is not vendored into this repository: it is cloned at an exact commit
# so the harness (Terminus-2) and the GPQA-Diamond adapter are byte-identical
# for anyone reproducing the run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARBOR_ROOT="${HARBOR_ROOT:-$REPO_ROOT/harbor}"
HARBOR_COMMIT="71c39eafbd134d43ae3f489b5e6488b2a157de65"  # 2026-09-06

command -v uv >/dev/null || {
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }

if [ ! -d "$HARBOR_ROOT/.git" ]; then
  git clone https://github.com/harbor-framework/harbor.git "$HARBOR_ROOT"
fi

# Pin. `fetch` first so the commit exists even in a shallow/older clone.
git -C "$HARBOR_ROOT" fetch --quiet origin "$HARBOR_COMMIT"
git -C "$HARBOR_ROOT" checkout --quiet "$HARBOR_COMMIT"

# --no-dev: the default dev group pulls every cloud backend and Tinker, none of
# which this experiment uses (local Docker + LiteLLM only).
uv sync --project "$HARBOR_ROOT" --no-dev

echo
echo "Harbor pinned at $HARBOR_COMMIT in $HARBOR_ROOT"
uv run --project "$HARBOR_ROOT" harbor --version || true
