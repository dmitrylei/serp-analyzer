#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
VENV_PY="$ROOT_DIR/.venv/bin/python"
VENV_ALEMBIC="$ROOT_DIR/.venv/bin/alembic"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

if [ ! -x "$VENV_ALEMBIC" ]; then
  echo "Missing alembic in venv. Run: pip install -e ."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

"$VENV_ALEMBIC" upgrade head
