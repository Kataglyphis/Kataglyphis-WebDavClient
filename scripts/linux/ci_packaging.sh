#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_CORE="${SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core"
CONTAINERHUB_DEPS="${SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts"

# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/build_common.sh"
# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/python_uv.sh"
# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/common.sh"

detect_workspace
build_init "$WORKSPACE_ROOT" "logs"

export PATH="$WORKSPACE_ROOT/flutter/bin:$PATH"
git config --global --add safe.directory "$WORKSPACE_ROOT" || true

build_run_step "Ensure patchelf" bash -c "
  if command -v patchelf >/dev/null 2>&1; then
    build_log 'patchelf already installed'
  else
    require_sudo
    apt_update_once
    \$SUDO apt-get install -y patchelf
  fi
"

VENV_SOURCES="$WORKSPACE_ROOT/.venv_packaging_sources"

build_run_step "Create Source Packaging Environment" bash -c "
  if [ -f '$VENV_SOURCES/bin/activate' ]; then
    info 'Using existing source packaging venv at $VENV_SOURCES'
  else
    info 'Creating source packaging venv at $VENV_SOURCES'
    uv venv '$VENV_SOURCES'
  fi
"

# shellcheck disable=SC1090
source "$VENV_SOURCES/bin/activate"

build_run_step "Sync Source Environment Dependencies" uv_sync_project --no-wxpython

build_run_step "Build Source Package" uv build

deactivate || true

export CYTHONIZE="True"

VENV_BINARIES="$WORKSPACE_ROOT/.venv_packaging_binaries"

build_run_step "Create Binary Packaging Environment" bash -c "
  if [ -f '$VENV_BINARIES/bin/activate' ]; then
    info 'Using existing binary packaging venv at $VENV_BINARIES'
  else
    info 'Creating binary packaging venv at $VENV_BINARIES'
    uv venv '$VENV_BINARIES'
  fi
"

# shellcheck disable=SC1090
source "$VENV_BINARIES/bin/activate"

build_run_step "Sync Binary Environment Dependencies" uv_sync_project --no-wxpython

build_run_step "Build Binary Package" uv build

mkdir -p dist repaired
shopt -s nullglob

build_log "Found wheels:"
ls -la dist || true

build_run_step "Repair Wheels with auditwheel" bash -c "
  for whl in dist/*.whl; do
    build_log \"Inspecting wheel: \$whl\"
    if auditwheel show \"\$whl\" >/dev/null 2>&1; then
      build_log \"  Platform wheel detected -> repairing: \$whl\"
      auditwheel repair \"\$whl\" -w repaired/ || { build_err \"auditwheel failed on \$whl\"; exit 1; }
    else
      build_log \"  Pure/Python wheel detected -> copying unchanged: \$whl\"
      cp \"\$whl\" repaired/
    fi
  done
"

rm -f dist/*.whl || true
mv repaired/*.whl dist/ || true
rmdir repaired || true

build_log "Final wheels in dist/:"
ls -la dist || true

build_finish 0