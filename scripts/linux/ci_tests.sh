#!/usr/bin/env bash
# ci_tests.sh - project wrapper around ContainerHub's generic Python CI test
# runner (linux/scripts/02-toolchain/python/ci_tests.sh).
#
# The local copy defaulted PACKAGE_NAME to 'orchestr_ant_ion' - the SIBLING
# project's name, copy-pasted. It only ever worked because CI passes the name
# explicitly. Upstream derives it from pyproject.toml, so that cannot recur.
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_DRIVER="${_SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/02-toolchain/python/ci_tests.sh"
[ -f "$_DRIVER" ] || { echo "Error: ContainerHub driver not found at $_DRIVER. Run: git submodule update --init --recursive ExternalLib/Kataglyphis-ContainerHub" >&2; exit 1; }

# WORKSPACE_ROOT must be THIS repo, not the submodule. Upstream's
# detect_workspace derives it from the sourcing script's own location, which for
# a delegated driver is .../ExternalLib/Kataglyphis-ContainerHub/linux/scripts -
# so every tool would run against the submodule tree. detect_workspace honours a
# pre-set value, and still overrides to /workspace in the container, so CI is
# unaffected.
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "${_SCRIPT_DIR}/../.." && pwd)}"

exec bash "$_DRIVER" "$@"
