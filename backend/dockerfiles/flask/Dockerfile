# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster
WORKDIR /app
COPY requirements/flask/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache \
    pip3 install -r requirements.txt
COPY scribe scribe
COPY app.py app.py