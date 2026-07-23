FROM python:3.12-slim

# ── System dependencies ───────────────────────────────────────────────────
# gcc    — psutil needs it on some platforms
# iputils-ping — ping plugin
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

# Downloaded plugins are stored here; mount a volume to persist them
# across restarts and avoid re-downloading on every start.
RUN mkdir -p plugins

VOLUME ["/app/plugins"]

# All config is passed at runtime — never bake credentials into the image.
# Required: PYMON_SERVER, PYMON_AGENTID, PYMON_API_KEY

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
