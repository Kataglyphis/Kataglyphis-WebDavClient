#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_ROOT="$(cd "$SCRIPT_DIR/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core" && pwd)"

# shellcheck disable=SC1090
source "$CONTAINERHUB_ROOT/build_common.sh" || { echo "Error: failed to source build_common.sh" >&2; exit 1; }

if [[ "${1:-}" == "-h" ||"${1:-}" == "--help" ]]; then
  cat <<EOF
Usage: ci_tests.sh [package_name] [py_versions_string]
  package_name defaults to \$PACKAGE_NAME or 'orchestr_ant_ion'
  py_versions_string defaults to \$PY_VERSIONS or '3.13 3.14'
  log file defaults to \$CI_TESTS_LOG_FILE or 'docs/test_results/ci_tests-<timestamp>.log'
EOF
  exit 0
fi

PACKAGE_NAME="${1:-${PACKAGE_NAME:-orchestr_ant_ion}}"
PY_VERSIONS="${2:-${PY_VERSIONS:- 3.13 3.14}}"
EXPERIMENTAL_VERSIONS="${EXPERIMENTAL_VERSIONS:-3.14t}"

LOG_FILE="${CI_TESTS_LOG_FILE:-docs/test_results/ci_tests-$(timestamp).log}"
mkdir -p "$(dirname "$LOG_FILE")"

exec > >(tee -a "$LOG_FILE") 2>&1

build_log "Logging to: $LOG_FILE"
build_log "PACKAGE_NAME=$PACKAGE_NAME"
build_log "PY_VERSIONS=$PY_VERSIONS"
build_log "EXPERIMENTAL_VERSIONS=$EXPERIMENTAL_VERSIONS"

git config --global --add safe.directory /workspace || true

mkdir -p docs/test_results

TEST_EXIT=0

for V in $PY_VERSIONS; do
  IS_EXPERIMENTAL=0
  for EXP_V in $EXPERIMENTAL_VERSIONS; do
    if [[ "$V" == "$EXP_V" ]]; then
      IS_EXPERIMENTAL=1
      break
    fi
  done

  if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
    build_log "[experimental] Running Python $V in non-blocking mode"
  else
    build_log "[stable] Running Python $V"
  fi

  VENV_DIR=".venv-${V}"

  if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
    if ! uv venv "$VENV_DIR" --python="${V}"; then
      build_log "[experimental] Failed to create venv for $V; continuing"
      continue
    fi
  else
    uv venv "$VENV_DIR" --python="${V}"
  fi

  # shellcheck disable=SC1090
  if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
    if ! source "$VENV_DIR/bin/activate"; then
      build_log "[experimental] Failed to activate venv for $V; continuing"
      rm -rf "$VENV_DIR"
      continue
    fi
  else
    source "$VENV_DIR/bin/activate"
  fi

  if [ -f uv.lock ]; then
    build_log "uv.lock found — using locked sync"
    if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
      if ! uv -v sync --active --locked --dev --all-extras; then
        build_log "[experimental] Dependency sync failed for $V; continuing"
        deactivate || true
        rm -rf "$VENV_DIR"
        continue
      fi
    else
      uv -v sync --active --locked --dev --all-extras
    fi
  else
    build_log "No uv.lock found — performing non-locked sync"
    if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
      if ! uv -v sync --active --dev --all-extras; then
        build_log "[experimental] Dependency sync failed for $V; continuing"
        deactivate || true
        rm -rf "$VENV_DIR"
        continue
      fi
    else
      uv -v sync --active --dev --all-extras
    fi
  fi

  if [[ "$IS_EXPERIMENTAL" -eq 1 ]]; then
    uv run --active pytest tests/unit -v \
      --cov="$PACKAGE_NAME"\
      --cov-report=term-missing \
      --cov-report="html:docs/test_results/coverage-html-${V}" \
      --cov-report="xml:docs/test_results/coverage-${V}.xml" \
      --junitxml="docs/test_results/report-${V}.xml" \
      --html="docs/test_results/pytest-report-${V}.html" \
      --self-contained-html \
      --md-report \
      --md-report-verbose=1 \
      --md-report-output "docs/test_results/pytest-report-${V}.md" \
      || build_log "[experimental] Unit tests failed for $V; continuing"
  else
    uv run --active pytest tests/unit -v \
      --cov="$PACKAGE_NAME" \
      --cov-report=term-missing \
      --cov-report="html:docs/test_results/coverage-html-${V}" \
      --cov-report="xml:docs/test_results/coverage-${V}.xml" \
      --junitxml="docs/test_results/report-${V}.xml" \
      --html="docs/test_results/pytest-report-${V}.html" \
      --self-contained-html \
      --md-report \
      --md-report-verbose=1 \
      --md-report-output "docs/test_results/pytest-report-${V}.md" || TEST_EXIT=$?
  fi

  uv run --active python bench/demo_cprofile.py || build_log "demo_cprofile.py skipped"
  uv run --active python bench/demo_line_profiler.py || build_log "demo_line_profiler.py skipped"
  uv run --active -m memory_profiler bench/demo_memory_profiling.py || build_log "memory profiling skipped"

  uv run --active py-spy record --rate 200 --duration 10 -o docs/test_results/profile.svg -- python bench/demo_py_spy.py \
    || build_log "py-spy profiling skipped (may require a longer-running process or py-spy missing)"

  uv run --active pytest bench/demo_pytest_benchmark.py || build_log "benchmark tests skipped or failed"

  deactivate || true
  rm -rf "$VENV_DIR"
done

build_finish "$TEST_EXIT"