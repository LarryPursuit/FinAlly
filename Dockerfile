# Stage 1: Build frontend static export
FROM node:20-slim AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + static files
FROM python:3.12-slim

# Install curl for healthcheck and uv for Python package management
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app/backend

# Install Python dependencies first (layer caching)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend source
COPY backend/ .
RUN uv sync --frozen --no-dev

# Copy frontend build output to static directory
COPY --from=frontend-build /build/out /app/backend/static

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Create db directory for volume mount (writable by appuser after volume mount)
RUN mkdir -p /app/db && chmod 777 /app/db

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENV PATH="/app/backend/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
