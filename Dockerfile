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

# App code + trained model (secrets, data, venv etc. are excluded by .dockerignore)
COPY . .

# Run as a non-root user; create folders that are mounted as volumes
RUN useradd --create-home --uid 1000 appuser \
 && mkdir -p /app/instance /app/static/uploads \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# 1) create the database tables if missing (the Milestone 2 "no such table: user" fix, now automatic)
# 2) start gunicorn: 1 worker so TensorFlow loads once, 4 threads
CMD ["sh", "-c", "python -c \"from app import create_app; a=create_app(); a.app_context().push(); a.extensions['sqlalchemy'].create_all(); print('DB ready')\" && exec gunicorn 'app:create_app()' --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 180"]
