#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m messenger.login_server --host 127.0.0.1 --port 9000
