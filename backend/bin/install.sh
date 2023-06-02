#!/bin/bash
set -Eeuo pipefail
set -x

python3 -m venv env
source env/bin/activate

pip install -r requirements.txt

mkdir -p files/audio_uploads
mkdir -p files/text_uploads
mkdir -p files/transcripts
mkdir -p files/summaries