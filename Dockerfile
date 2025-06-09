# Use a minimal Python image (Alpine)
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libffi-dev make git && \
    rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS builder

# Create app directory
WORKDIR /app

# Copy project files
COPY ./makefile .
COPY ./README.md .
COPY ./pyproject.toml .
COPY ./codantix ./codantix
COPY ./tests ./tests
COPY ./.python-version .
COPY ./codantix.config.json .

# Install dependencies and the package
RUN make sync
RUN uv pip install -e ".[dev]"
RUN uv pip install pytest-timeout

# Development environment setup
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command for development
CMD ["bash"]