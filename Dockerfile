# CropGuard AI - production image
# Small base image: Debian slim + Python 3.10 (same Python as the Milestone 2 VM)
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_DEBUG=false

# Only the runtime system libraries TensorFlow / OpenCV need; apt lists removed in the same layer
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so this big layer is cached and only rebuilt when requirements.txt changes.
# Upgrade pip first (the base image's pip is too old for the PyTorch index),
# then CPU-only PyTorch: avoids ~3 GB of NVIDIA GPU libraries we can't use.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
 && pip install --no-cache-dir -r requirements.txt

# Non-root user and runtime folders, created BEFORE the code is copied so a
# code-only change rebuilds just the COPY layer (fast CI builds from cache).
RUN useradd --create-home --uid 1000 appuser \
 && mkdir -p /app/instance /app/static/uploads \
 && chown -R appuser:appuser /app

# App code + trained model (secrets, data, venv etc. are excluded by .dockerignore)
COPY --chown=appuser:appuser . .

# Version stamp: CI passes the git commit SHA; /health reports it so the
# pipeline can verify which version is serving traffic (and after a rollback).
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
USER appuser

EXPOSE 5000

# 1) apply database migrations (Alembic, migrations/ folder) -- creates/updates tables
#    in Cloud SQL; replaces the Milestone 3 create_all() shortcut
# 2) start gunicorn: 1 worker so TensorFlow loads once, 4 threads
ENV FLASK_APP=run.py
CMD ["sh", "-c", "flask db upgrade && exec gunicorn 'app:create_app()' --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 180"]
