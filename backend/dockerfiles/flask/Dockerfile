# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster
WORKDIR /app
RUN mkdir -p files/audio_uploads && mkdir -p files/transcripts && mkdir -p files/summaries
COPY requirements/flask/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip && pip install -r requirements.txt
COPY scribe scribe
COPY app.py app.py