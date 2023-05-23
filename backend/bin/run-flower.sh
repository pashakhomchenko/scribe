#!/bin/bash
set -Eeuo pipefail
set -x

celery -A app.celery flower