# Use Python 3.13 as base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set work directory
WORKDIR /app

# Copy dependency files first (for caching)
# Copy dependency files first (for caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies (exclude dev dependencies for production image)
RUN poetry install --no-interaction --no-ansi --no-root --no-dev

# Copy application code (be specific to avoid copying junk)
COPY backend ./backend

# Default command (can be overridden in docker-compose)
# Using shell form to allow variable expansion if needed
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port 8000"]