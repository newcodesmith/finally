# FinAlly — Multi-stage Docker build
# Stage 1: Build Next.js static export
# Stage 2: Python backend serving static files + API

# ---------------------------------------------------------------------------
# Stage 1: Frontend build
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /build/frontend

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install

# Copy source and build static export
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Backend + serve
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/backend

# Install Python dependencies first (layer caching)
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy backend source
COPY backend/ ./

# Copy frontend build output to where main.py expects it (/app/static/)
COPY --from=frontend-build /build/frontend/out/ /app/static/

# Create db directory for SQLite volume mount
RUN mkdir -p /app/db

# Set environment defaults
ENV DB_PATH=/app/db/finally.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check — verify the API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
