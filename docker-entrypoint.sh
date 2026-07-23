#!/bin/sh
set -e

# Strip surrounding quotes (Portainer / some runtimes pass them literally)
strip_quotes() { echo "$1" | sed 's/^["'\'']*//;s/["'\'']*$//'; }

PYMON_SERVER=$(strip_quotes "${PYMON_SERVER:-}")
PYMON_AGENTID=$(strip_quotes "${PYMON_AGENTID:-}")
PYMON_API_KEY=$(strip_quotes "${PYMON_API_KEY:-}")

if [ -z "$PYMON_SERVER" ] || [ -z "$PYMON_AGENTID" ] || [ -z "$PYMON_API_KEY" ]; then
    echo "ERROR: PYMON_SERVER, PYMON_AGENTID and PYMON_API_KEY are required." >&2
    exit 1
fi

echo "pymon-agent: server=${PYMON_SERVER} agentid=${PYMON_AGENTID}"

exec python -u agent.py \
    --server   "$PYMON_SERVER" \
    --agentid  "$PYMON_AGENTID" \
    --api-key  "$PYMON_API_KEY"
