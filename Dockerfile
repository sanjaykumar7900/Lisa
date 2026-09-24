# ────────────────────────────────────────────────
# Stage 1: Build frontend
# ────────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY frontend .
RUN npm run build

# ────────────────────────────────────────────────
# Stage 2: Runtime (backend + static frontend)
# ────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && playwright install --with-deps chromium

# Copy backend source
COPY backend /app/backend

# Copy built frontend into a static directory the backend can serve
COPY --from=frontend-build /app/frontend/dist /app/static

ENV PYTHONPATH=/app/backend
ENV NVIDIA_API_KEY=""
ENV DATABASE_URL="sqlite+aiosqlite:////app/backend/lisa.db"

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
