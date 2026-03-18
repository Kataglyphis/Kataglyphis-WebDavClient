#!/usr/bin/env bash
set -euo pipefail

COVERAGE_VERSION="${1:-3.13}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_CORE="${SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/01-core"

# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/build_common.sh"
# shellcheck disable=SC1090
source "$CONTAINERHUB_CORE/python_uv.sh"

detect_workspace
build_init "$WORKSPACE_ROOT" "logs"

export PATH="$WORKSPACE_ROOT/flutter/bin:$PATH"
git config --global --add safe.directory "$WORKSPACE_ROOT" || true

VENV_DIR="$WORKSPACE_ROOT/.venv-docs"

build_run_step "Setup Docs Virtual Environment" bash -c "
  if [ -f '$VENV_DIR/bin/activate' ]; then
    info 'Using existing docs venv at $VENV_DIR'
  else
    info 'Creating docs venv at $VENV_DIR'
    uv venv '$VENV_DIR'
  fi
"

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

build_run_step "Sync Dependencies" uv_sync_project --no-wxpython

cp "$WORKSPACE_ROOT/README.md" "$WORKSPACE_ROOT/docs/source/README.md"
cp "$WORKSPACE_ROOT/CHANGELOG.md" "$WORKSPACE_ROOT/docs/source/CHANGELOG.md"

SRC="$WORKSPACE_ROOT/docs/test_results"
STATIC_DIR="$WORKSPACE_ROOT/docs/source/_static"
COVERAGE_DST="$STATIC_DIR/coverage"
TEST_RESULTS_DST="$STATIC_DIR/test_results"

mkdir -p "$COVERAGE_DST" "$TEST_RESULTS_DST"

build_log "Looking for coverage HTML in $SRC ..."
if [ ! -d "$SRC" ]; then
  build_log "No test results directory found in $SRC."
elif [ -d "$SRC/coverage-html-${COVERAGE_VERSION}" ]; then
  cp -r "$SRC/coverage-html-${COVERAGE_VERSION}/." "$COVERAGE_DST/"
  build_log "Copied $SRC/coverage-html-${COVERAGE_VERSION} -> $COVERAGE_DST/"
elif [ -d "$SRC/coverage" ]; then
  cp -r "$SRC/coverage/." "$COVERAGE_DST/"
  build_log "Copied $SRC/coverage -> $COVERAGE_DST/"
elif [ -d "$SRC/htmlcov" ]; then
  cp -r "$SRC/htmlcov/." "$COVERAGE_DST/"
  build_log "Copied $SRC/htmlcov -> $COVERAGE_DST/"
else
  found=$(find "$SRC" -maxdepth 3 -type f -name index.html | grep -v pytest-report | head -n1 || true)
  if [ -n "$found" ]; then
    base=$(dirname "$found")
    cp -r "$base/." "$COVERAGE_DST/"
    build_log "Copied discovered coverage HTML from $base -> $COVERAGE_DST/"
  else
    build_log "No coverage HTML folder found in $SRC."
  fi
fi

if [ -f "$SRC/coverage-${COVERAGE_VERSION}.xml" ]; then
  cp "$SRC/coverage-${COVERAGE_VERSION}.xml" "$STATIC_DIR/coverage.xml"
  build_log "Copied coverage-${COVERAGE_VERSION}.xml -> $STATIC_DIR/coverage.xml"
elif [ -f "$SRC/coverage.xml" ]; then
  cp "$SRC/coverage.xml" "$STATIC_DIR/coverage.xml"
  build_log "Copied coverage.xml -> $STATIC_DIR/coverage.xml"
fi

build_log "Copying pytest HTML reports..."
for html_file in "$SRC"/pytest-report-*.html; do
  if [ -f "$html_file" ]; then
    cp "$html_file" "$TEST_RESULTS_DST/"
    build_log "Copied $(basename "$html_file") to $TEST_RESULTS_DST/"
  fi
done

for xml_file in "$SRC"/report-*.xml; do
  if [ -f "$xml_file" ]; then
    cp "$xml_file" "$TEST_RESULTS_DST/"
    build_log "Copied $(basename "$xml_file") to $TEST_RESULTS_DST/"
  fi
done

for md_file in "$SRC"/pytest-report-*.md; do
  if [ -f "$md_file" ]; then
    cp "$md_file" "$STATIC_DIR/"
  fi
done

build_run_step "Build Sphinx Documentation" bash -c "cd '$WORKSPACE_ROOT/docs' && make html"

if [ "$WORKSPACE_ROOT" = "/workspace" ] && [ -d /workspace ]; then
  OWNER_UID=$(stat -c "%u" /workspace)
  OWNER_GID=$(stat -c "%g" /workspace)
  build_log "Fixing ownership of docs to ${OWNER_UID}:${OWNER_GID}"
  chown -R "${OWNER_UID}:${OWNER_GID}" "$WORKSPACE_ROOT/docs" || true
fi

build_finish 0