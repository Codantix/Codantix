# Use a minimal Python image (Alpine)
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libffi-dev make && \
    rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS builder

# Create app directory
WORKDIR /app

# Copy project files
COPY ./makefile .
COPY ./README.md .
COPY ./pyproject.toml .
COPY ./codantix/ .
COPY ./tests/ .
COPY ./.python-version .
COPY ./codantix.config.json .

RUN make sync
RUN uv sync --all-groups

# Expose Ollama's default port
EXPOSE 11434

# Start Ollama as a background service, then run tests
CMD ollama serve & sleep 5 && make test