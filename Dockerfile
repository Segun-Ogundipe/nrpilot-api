# ------------------------
# Builder Environment
# ------------------------
FROM python:3.13-slim AS builder

# 1. Enable bytecode compilation
# 2. Copy from the cache instead of linking since it's a mounted volume
# 3. Omit development dependencies
# 4. Use uv.lock as it is, fail if uv locked needs to be updated
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_LOCKED=1

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv  /usr/local/bin/uv

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project

# Copy source code
COPY . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# ------------------------
# Runtime Environment
# ------------------------
FROM python:3.13-slim

# 1. Activate the virtual environment on the system PATH
# 2. Prevent Python from buffering stdout/stderr
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-priviledged user for security
# RUN useradd --create-home nrpilot && chown -R nrpilot:nrpilot /app
RUN groupadd --system --gid 999 nrpilot \
    && useradd --system --gid 999 --uid 999 --create-home nrpilot

# Copy virtual env and compiled source code from builder
COPY --from=builder --chown=nrpilot:nrpilot /app /app

USER nrpilot

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
