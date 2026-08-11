#!/usr/bin/env bash
# setup-dependencies.sh - project wrapper around ContainerHub's dependency
# installer (linux/scripts/02-toolchain/setup-dependencies.sh).
#
# The driver moved from linux/scripts/ into linux/scripts/02-toolchain/ during
# the scripts reorg; this wrapper still pointed at the old top-level path, so
# `source` of a nonexistent file aborted under `set -e` with only a bash
# "No such file or directory" and no hint that the submodule layout had changed.
# Guarded explicitly now so the next move fails with an actionable message.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_SETUP_SCRIPT="$SCRIPT_DIR/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/02-toolchain/setup-dependencies.sh"

if [ ! -f "$CONTAINERHUB_SETUP_SCRIPT" ]; then
  echo "Error: ContainerHub driver not found at $CONTAINERHUB_SETUP_SCRIPT." >&2
  echo "Run: git submodule update --init --recursive ExternalLib/Kataglyphis-ContainerHub" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$CONTAINERHUB_SETUP_SCRIPT"
