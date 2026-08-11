#!/usr/bin/env bash
# ci_static_analysis.sh - project wrapper around ContainerHub's generic Python
# static-analysis runner (linux/scripts/02-toolchain/python/ci_static_analysis.sh).
#
# The local copy reimplemented the same codespell/bandit/vulture/ruff/ty pipeline
# with its own venv lifecycle. Upstream owns both and derives the package name
# from pyproject.toml.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/containerhub.sh"

containerhub_exec "linux/scripts/02-toolchain/python/ci_static_analysis.sh" "$@"
