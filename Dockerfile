# Stage 1: Build frontend static export
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime — Python backend serving static frontend
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy backend dependency files first for layer caching
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/

# Install Python dependencies
WORKDIR /app/backend
RUN uv sync --no-dev --frozen

# Copy backend source code
COPY backend/app ./app

# Copy frontend build output to where main.py expects it
# main.py resolves static dir as: os.path.join(os.path.dirname(__file__), "..", "..", "static")
# From /app/backend/app/main.py -> /app/static
COPY --from=frontend-builder /app/frontend/out /app/static

# Create database directory
WORKDIR /app/backend
RUN mkdir -p /app/db

# Security: run as non-root user
RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app/db /app/backend

VOLUME /app/db

USER appuser

EXPOSE 8000

ENV UV_NO_CACHE=1
ENV DB_PATH=/app/db/finally.db

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
