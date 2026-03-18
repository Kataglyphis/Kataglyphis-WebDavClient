#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERHUB_SETUP_SCRIPT="$SCRIPT_DIR/../../ExternalLib/Kataglyphis-ContainerHub/linux/scripts/setup-dependencies.sh"

# shellcheck disable=SC1090
source "$CONTAINERHUB_SETUP_SCRIPT"