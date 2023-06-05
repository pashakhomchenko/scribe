# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg libcurl4-gnutls-dev librtmp-dev build-essential
COPY requirements/transcribe/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache \
    pip3 install -r requirements.txt
COPY transcribe.py transcribe.py