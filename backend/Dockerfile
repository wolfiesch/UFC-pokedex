# syntax=docker/dockerfile:1.5

FROM python:3.11-slim AS uv-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        cmake \
        libopenblas-dev \
        liblapack-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        libpng-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.29 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv venv /opt/venv \
    && uv pip sync --python /opt/venv/bin/python --no-dev \
    && rm -rf ${UV_CACHE_DIR}

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgl1 \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        libpng16-16 \
        libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=uv-builder --chown=appuser:appgroup /opt/venv /opt/venv
COPY --chown=appuser:appgroup backend ./backend

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
