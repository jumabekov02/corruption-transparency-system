# Start from an official slim Python image (small Linux + Python 3.11 preinstalled).
FROM python:3.11-slim

# Environment tweaks: don't write .pyc files, flush logs immediately, quiet pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# All following commands run inside /app in the image.
WORKDIR /app

# System packages needed to build psycopg2 (the Postgres driver).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first, then install. Docker caches this layer, so
# changing app code later doesn't reinstall dependencies every build.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Now copy the application code.
COPY . .

# Document that the container serves on port 8000.
EXPOSE 8000

# Default command (docker-compose overrides this to add --reload in dev).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
