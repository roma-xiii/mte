FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock .
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/exchanges/pyproject.toml packages/exchanges/pyproject.toml
COPY packages/strategies/pyproject.toml packages/strategies/pyproject.toml
COPY packages/trading_controls/pyproject.toml packages/trading_controls/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml

RUN uv sync --no-dev --frozen --no-build-isolation

COPY packages/ packages/
COPY apps/ apps/

CMD ["uv", "run", "--directory", "apps/worker", "python", "worker.py"]
