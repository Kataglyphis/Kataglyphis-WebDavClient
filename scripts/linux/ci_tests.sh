#!/usr/bin/env bash
# ci_tests.sh - project wrapper around ContainerHub's generic Python CI test
# runner (linux/scripts/02-toolchain/python/ci_tests.sh).
#
# The local copy defaulted PACKAGE_NAME to 'orchestr_ant_ion' - the SIBLING
# project's name, copy-pasted. It only ever worked because CI passes the name
# explicitly. Upstream derives it from pyproject.toml, so that cannot recur.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/containerhub.sh"

containerhub_exec "linux/scripts/02-toolchain/python/ci_tests.sh" "$@"
