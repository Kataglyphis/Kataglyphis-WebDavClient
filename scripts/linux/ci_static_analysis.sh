#!/usr/bin/env bash
set -euo pipefail

ARCH="${1:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_CORE="${SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core"

# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/build_common.sh"
# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/python_uv.sh"

detect_workspace
build_init "$WORKSPACE_ROOT" "logs"

build_log "Starting static analysis pipeline"

if [ -d /workspace ]; then
  git config --global --add safe.directory /workspace || true
fi

VENV_DIR=".venv_static_analysis"

build_run_step "Setup Virtual Environment" bash -c "
  if [ -d '$VENV_DIR' ]; then
    build_log 'Using existing virtual environment at: $VENV_DIR'
  else
    build_log 'Creating virtual environment at: $VENV_DIR'
    uv venv '$VENV_DIR' --clear
  fi
"

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

build_run_step "Sync Dependencies" uv_sync_project --no-wxpython

build_run_step "Run codespell" uv_run codespell kataglyphis_webdavclient tests docs/source/conf.py setup.py README.md || true

build_run_step "Run bandit" uv_run bandit -r kataglyphis_webdavclient \
  -x tests,.venv,.venv_static_analysis,ExternalLib,archive,docs/test_results || true

build_run_step "Run vulture" uv_run vulture kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_run_step "Run ruff format" uv_run ruff format kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_run_step "Run ruff check --fix" uv_run ruff check --fix kataglyphis_webdavclient tests docs/source/conf.py setup.py || true

build_run_step "Run ty check" uv_run ty check || true

deactivate || true
uv_venv_remove "$VENV_DIR"

build_log "Static analysis pipeline finished"

if [ -n "$ARCH" ]; then
  build_log "Static analysis completed for arch: $ARCH"
fi

build_finish 0