#!/usr/bin/env bash
set -euo pipefail

ARCH="${1:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_ROOT="$(cd "$SCRIPT_DIR/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core" && pwd)"

# shellcheck disable=SC1090
source "$CONTAINERHUB_ROOT/build_common.sh" || { echo "Error: failed to source build_common.sh" >&2; exit 1; }

build_init "${WORKSPACE_ROOT:-$PWD}" "logs"

build_log "Starting static analysis pipeline"

if [ -d /workspace ]; then
  git config --global --add safe.directory /workspace || true
fi

VENV_DIR=".venv_static_analysis"
VENV_WAS_PRESENT=0

if [ -d "$VENV_DIR" ]; then
  build_log "Using existing virtual environment at: $VENV_DIR"
  VENV_WAS_PRESENT=1
else
  build_log "Creating virtual environment at: $VENV_DIR"
  UV_VENV_CLEAR=1 uv venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [ -f uv.lock ]; then
  build_log "uv.lock found — using locked sync"
  uv -v sync --active --locked --dev --all-extras --no-build-isolation-package wxpython
else
  build_log "No uv.lock found — performing non-locked sync"
  uv -v sync --active --dev --all-extras --no-build-isolation-package wxpython
fi

build_log "Running codespell"
uv run --active codespell kataglyphis_webdavclient tests docs/source/conf.py setup.py README.md || true

build_log "Running bandit"
uv run --active bandit -r kataglyphis_webdavclient \
  -x tests,.venv,.venv_static_analysis,ExternalLib,archive,docs/test_results || true

build_log "Running vulture"
uv run --active vulture kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_log "Running ruff format"
uv run --active ruff format kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_log "Running ruff check --fix"
uv run --active ruff check --fix kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_log "Running ty check"
uv run --active ty check || true

deactivate || true

if [ "$VENV_WAS_PRESENT" -eq 0 ]; then
  build_log "Removing temporary virtual environment: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

build_log "Static analysis pipeline finished"

if [ -n "$ARCH" ]; then
  build_log "Static analysis completed for arch: $ARCH"
fi

build_finish 0