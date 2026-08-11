#!/usr/bin/env bash
# ci_packaging.sh - project wrapper around ContainerHub's generic Python package
# builder (linux/scripts/02-toolchain/python/ci_packaging.sh).
#
# Keeps ONE local step: patchelf. The binary wheel build needs it on the runner
# and upstream's driver does not install it. Left here rather than upstreamed
# because no second consumer needs it - the two-consumer rule in ContainerHub's
# AGENTS.md.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/containerhub.sh"

if ! command -v patchelf >/dev/null 2>&1; then
  echo "[INFO] Installing patchelf (needed to repair the binary wheel's RPATHs)"
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
  $SUDO apt-get update -y && $SUDO apt-get install -y patchelf
fi

containerhub_exec "linux/scripts/02-toolchain/python/ci_packaging.sh" "$@"
