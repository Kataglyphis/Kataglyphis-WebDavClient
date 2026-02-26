#!/usr/bin/env bash
set -euo pipefail

ARCH="${1:-}"  # optional; kept for parity with workflow matrix

log_info() {
  echo "[ci-static-analysis] $1"
}

log_info "Starting static analysis pipeline"

git config --global --add safe.directory /workspace || true

VENV_DIR=".venv_static_analysis"
VENV_WAS_PRESENT=0

if [ -d "$VENV_DIR" ]; then
  log_info "Using existing virtual environment at: $VENV_DIR"
  VENV_WAS_PRESENT=1
else
  log_info "Creating virtual environment at: $VENV_DIR"
  UV_VENV_CLEAR=1 uv venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [ -f uv.lock ]; then
  log_info "uv.lock found — using locked sync"
  uv -v sync --active --locked --dev --all-extras --no-build-isolation-package wxpython
else
  log_info "No uv.lock found — performing non-locked sync"
  uv -v sync --active --dev --all-extras --no-build-isolation-package wxpython
fi

log_info "Running codespell"
uv run --active codespell kataglyphis_webdavclient tests docs/source/conf.py setup.py README.md || true
# uv run --active mypy kataglyphis_webdavclient tests docs/source/conf.py setup.py || true
log_info "Running bandit"
uv run --active bandit -r kataglyphis_webdavclient \
  -x tests,.venv,.venv_static_analysis,ExternalLib,archive,docs/test_results || true
log_info "Running vulture"
uv run --active vulture kataglyphis_webdavclient tests docs/source/conf.py setup.py || true
log_info "Running ruff format"
uv run --active ruff format kataglyphis_webdavclient tests docs/source/conf.py setup.py || true
log_info "Running ruff check --fix"
uv run --active ruff check --fix kataglyphis_webdavclient tests docs/source/conf.py setup.py || true
log_info "Running ty check"
uv run --active ty check || true

if [ "$VENV_WAS_PRESENT" -eq 0 ]; then
  log_info "Removing temporary virtual environment: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

log_info "Static analysis pipeline finished"

if [ -n "$ARCH" ]; then
  log_info "Static analysis completed for arch: $ARCH"
fi
