#!/bin/bash
set -Eeuo pipefail
set -x

watchmedo auto-restart -d scribe/ -p "tasks.py" -- celery -A scribe.tasks.app worker -l info