# syntax=docker/dockerfile:1.5

FROM python:3.11-slim AS uv-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

COPY pyproject.toml uv.lock ./

RUN uv venv /opt/venv
RUN uv export --frozen --no-dev --format requirements-txt --output requirements.txt
RUN uv pip install --python /opt/venv/bin/python --upgrade pip \
    && uv pip install --python /opt/venv/bin/python --requirement requirements.txt \
    && rm -rf /root/.cache/pip

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY --from=uv-builder /opt/venv /opt/venv
COPY backend ./backend
COPY uv.lock pyproject.toml ./

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
