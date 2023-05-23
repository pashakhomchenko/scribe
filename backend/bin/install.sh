#!/bin/bash
set -Eeuo pipefail
set -x

python3 -m venv env
source env/bin/activate

pip install -r requirements.txt

mkdir -p audio_uploads
mkdir -p text_uploads
mkdir -p transcripts
mkdir -p summaries