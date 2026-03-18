#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_ROOT="$(cd "$SCRIPT_DIR/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core" && pwd)"

# shellcheck disable=SC1090
source "$CONTAINERHUB_ROOT/build_common.sh" || { echo "Error: failed to source build_common.sh" >&2; exit 1; }

detect_workspace

build_init "$WORKSPACE_ROOT" "logs"

export PATH="$WORKSPACE_ROOT/flutter/bin:$PATH"
git config --global --add safe.directory "$WORKSPACE_ROOT" || true

build_step "Ensure patchelf" bash -c "
  if command -v patchelf >/dev/null 2>&1; then
    build_log 'patchelf already installed'
  else
    SUDO_CMD=''
    if command -v sudo >/dev/null 2>&1; then
      SUDO_CMD='sudo'
    fi
    \$SUDO_CMD apt-get update
    \$SUDO_CMD apt-get install -y patchelf
  fi
"

VENV_SOURCES="$WORKSPACE_ROOT/.venv_packaging_sources"
build_step "Create Source Packaging Environment" bash -c "
  if [ -f '$VENV_SOURCES/bin/activate' ]; then
    info 'Using existing source packaging venv at $VENV_SOURCES'
  else
    info 'Creating source packaging venv at $VENV_SOURCES'
    uv venv '$VENV_SOURCES'
  fi
"

# shellcheck disable=SC1090
source "$VENV_SOURCES/bin/activate"

build_step "Sync Source Environment Dependencies" bash -c "
  if [ -f uv.lock ]; then
    info 'uv.lock found — using locked sync'
    uv -v sync --active --locked --dev --all-extras --no-build-isolation-package wxpython
  else
    info 'No uv.lock found — performing non-locked sync'
    uv -v sync --active --dev --all-extras --no-build-isolation-package wxpython
  fi
"

build_step "Build Source Package" uv build

deactivate || true

export CYTHONIZE="True"

VENV_BINARIES="$WORKSPACE_ROOT/.venv_packaging_binaries"
build_step "Create Binary Packaging Environment" bash -c "
  if [ -f '$VENV_BINARIES/bin/activate' ]; then
    info 'Using existing binary packaging venv at $VENV_BINARIES'
  else
    info 'Creating binary packaging venv at $VENV_BINARIES'
    uv venv '$VENV_BINARIES'
  fi
"

# shellcheck disable=SC1090
source "$VENV_BINARIES/bin/activate"

build_step "Sync Binary Environment Dependencies" bash -c "
  if [ -f uv.lock ]; then
    info 'uv.lock found — using locked sync'
    uv -v sync --active --locked --dev --all-extras --no-build-isolation-package wxpython
  else
    info 'No uv.lock found — performing non-locked sync'
    uv -v sync --active --dev --all-extras --no-build-isolation-package wxpython
  fi
"

build_step "Build Binary Package" uv build

mkdir -p dist repaired
shopt -s nullglob

build_log "Found wheels:"
ls -la dist || true

build_step "Repair Wheels with auditwheel" bash -c "
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