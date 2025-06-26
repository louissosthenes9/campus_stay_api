# Use the official Python image as the base image
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgdal-dev \
    gdal-bin \
    python3-gdal \
    binutils \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy only the dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock* /app/

# Install Python dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "campus_stay.wsgi:application", "--bind", "0.0.0.0:8000"]

# Development stage (optional, uncomment if needed)
# FROM base as development
# RUN pip install -r requirements/dev.txt
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage (uncomment when ready)
 FROM base as production
 COPY --from=base /app /app
 CMD ["gunicorn", "campus_stay.wsgi:application", "--bind", "0.0.0.0:8000"]