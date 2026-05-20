#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m messenger.client --id alice --server-host 127.0.0.1 --server-port 9000 --listen-port 10001
