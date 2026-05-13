# ─── Build Stage ─────────────────────────────────────────────────────────────
FROM python:3.10-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libgomp1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create upload directory
RUN mkdir -p static/uploads

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "app:create_app()", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
