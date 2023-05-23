#!/bin/bash
set -Eeuo pipefail
set -x

flask --app scribe --debug run --host 0.0.0.0 --port 5000