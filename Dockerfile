# Build stage: compile dependencies (psycopg2 needs gcc and the libpq headers)
FROM python:3.13-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage: only the runtime libraries, no compiler and no pip
FROM python:3.13-slim

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --no-create-home app

COPY --from=builder /install /usr/local

# pip is not needed at runtime and ships vendored packages with known vulnerabilities
RUN python -m pip uninstall -y pip setuptools wheel || true

WORKDIR /code

COPY --chown=app . .

COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

USER app

# Default command (overridden by docker-compose)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
