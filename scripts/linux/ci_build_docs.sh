#!/usr/bin/env bash
# ci_build_docs.sh - project wrapper around ContainerHub's generic Python
# documentation builder (linux/scripts/02-toolchain/python/ci_build_docs.sh).
#
# The local copy also put $WORKSPACE_ROOT/flutter/bin on PATH; this is a Python
# project with no Flutter step, so that is dropped rather than ported.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/containerhub.sh"

containerhub_exec "linux/scripts/02-toolchain/python/ci_build_docs.sh" "$@"
