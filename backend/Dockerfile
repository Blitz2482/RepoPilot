FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY schemas/ /app/schemas/
COPY agents.md /app/agents.md
COPY AGENTS.md /app/AGENTS.md
COPY CONTEXT_PACK.md /app/CONTEXT_PACK.md
COPY .bob/ /app/.bob/

RUN useradd --create-home --uid 10001 repopilot \
    && mkdir -p /tmp/repopilot /tmp/bob_logs \
    && chown -R repopilot:repopilot /app /tmp/repopilot /tmp/bob_logs

USER repopilot

EXPOSE 8000
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + str(__import__('os').environ.get('PORT','8000')) + '/health', timeout=4)"

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
