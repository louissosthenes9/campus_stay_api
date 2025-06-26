# Use the official Python image as the base image
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libgdal-dev \
    libgdal28 \
    gdal-bin \
    python3-gdal \
    binutils \
    libproj-dev \
    libgeos-dev \
    libgeos-c1v5 \
    libspatialite-dev \
    libspatialindex-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Configure Poetry
RUN poetry config virtualenvs.create false \
    && poetry config cache-dir $POETRY_CACHE_DIR

# Copy only the dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock* /app/

# Verify GDAL installation and get version
RUN gdal-config --version

# Install Python dependencies with GDAL support
RUN poetry install --only=main --no-interaction --no-ansi --no-root \
    && rm -rf $POETRY_CACHE_DIR

# Copy the rest of the application
COPY . /app/

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose the port the app runs on
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production

# Switch back to root to install production dependencies
USER root

# Install gunicorn for production
RUN poetry add gunicorn

# Switch back to app user
USER app

# Production command
CMD ["gunicorn", "campus_stay.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]