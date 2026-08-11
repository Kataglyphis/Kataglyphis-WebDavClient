#!/usr/bin/env bash
# ci_packaging.sh - project wrapper around ContainerHub's generic Python package
# builder (linux/scripts/02-toolchain/python/ci_packaging.sh).
#
# Keeps ONE local step: patchelf. The binary wheel build needs it on the runner
# and upstream's driver does not install it. Left here rather than upstreamed
# because no second consumer needs it - the two-consumer rule in ContainerHub's
# AGENTS.md.
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_DRIVER="${_SCRIPT_DIR}/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/02-toolchain/python/ci_packaging.sh"
[ -f "$_DRIVER" ] || { echo "Error: ContainerHub driver not found at $_DRIVER. Run: git submodule update --init --recursive ExternalLib/Kataglyphis-ContainerHub" >&2; exit 1; }

if ! command -v patchelf >/dev/null 2>&1; then
  echo "[INFO] Installing patchelf (needed to repair the binary wheel's RPATHs)"
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
  $SUDO apt-get update -y && $SUDO apt-get install -y patchelf
fi

# WORKSPACE_ROOT must be THIS repo, not the submodule. Upstream's
# detect_workspace derives it from the sourcing script's own location, which for
# a delegated driver is .../ExternalLib/Kataglyphis-ContainerHub/linux/scripts -
# so every tool would run against the submodule tree. detect_workspace honours a
# pre-set value, and still overrides to /workspace in the container, so CI is
# unaffected.
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "${_SCRIPT_DIR}/../.." && pwd)}"

exec bash "$_DRIVER" "$@"
