#!/usr/bin/env bash
set -Eeuo pipefail
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest "$@"
