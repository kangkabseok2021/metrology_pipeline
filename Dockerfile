FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libopencv-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN pip install uv
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
# Prevent OpenBLAS from spawning its own thread pool inside each worker process
ENV OMP_NUM_THREADS=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER nobody

HEALTHCHECK CMD python -c 'import leo_tracker; print("ok")'

ENTRYPOINT ["leo-tracker"]
CMD ["--help"]
