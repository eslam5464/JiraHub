# Multi-stage build for optimal size and speed
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    libffi-dev

# Set uv configuration for production
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_VERSION=0.10.2

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Create virtual environment at /app/.venv and install dependencies
RUN uv sync --frozen --no-dev --allow-insecure-host files.pythonhosted.org --no-cache-dir --no-wheels

# Production stage
FROM python:3.13-alpine AS production

# Install runtime dependencies only
RUN apk add --no-cache \
    postgresql-libs \
    curl

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    WORKERS_COUNT=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Create a non-privileged user and group for running the application
RUN addgroup -g 1001 -S uvicorn \
    && adduser -u 1001 -S uvicorn -G uvicorn \
    && mkdir -p /home/uvicorn \
    && chown -R uvicorn:uvicorn /home/uvicorn \
    && chown -R uvicorn:uvicorn /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=uvicorn:uvicorn /app/.venv /app/.venv

# Copy application code (single COPY group with proper ownership)
COPY --chown=uvicorn:uvicorn ./app ./app
COPY --chown=uvicorn:uvicorn ./alembic ./alembic
COPY --chown=uvicorn:uvicorn ./alembic.ini ./alembic.ini
COPY --chown=uvicorn:uvicorn ./.streamlit ./.streamlit
COPY --chown=uvicorn:uvicorn ./entrypoint.sh ./entrypoint.sh

# Copy uv from builder stage
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Create data and logs directories with proper ownership
RUN mkdir -p /app/data /app/logs && \
    chown -R uvicorn:uvicorn /app/data /app/logs && \
    chmod 755 /app/entrypoint.sh

# Remove Streamlit's default lockfile and credentials storage location
RUN rm -rf /root/.streamlit

# Switch to non-privileged user
USER uvicorn

EXPOSE 8501

# Health check for orchestrators (Kubernetes, Docker Compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Use entrypoint script for proper signal handling (PID 1)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
