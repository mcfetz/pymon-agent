# Deployment

## Pipeline-Ablauf

```
git push main
    │
    ▼
GitHub Actions (.github/workflows/docker.yml)
    │
    ├─ Build multi-arch image (amd64 + arm64)
    ├─ Push → ghcr.io/mcfetz/pymon-agent:latest
    │
    └─ POST https://portainer.familie-heise.de/api/webhooks/...
              │
              ▼
         Portainer pulls new image and restarts the container
```

## GitHub Secret einrichten

1. GitHub → Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
   - Name: `PORTAINER_WEBHOOK_URL`
   - Value: Portainer-Webhook-URL für den pymon-agent Stack
3. Save

## Image

| Registry | Image |
|----------|-------|
| GitHub Container Registry | `ghcr.io/mcfetz/pymon-agent` |

## Konfiguration (Laufzeit-Env-Vars)

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `PYMON_SERVER` | ✅ | URL des pymon-server inkl. `/api`, z.B. `https://pymon.example.com/api` |
| `PYMON_AGENTID` | ✅ | Agent-ID wie in `agents.json` konfiguriert |
| `PYMON_API_KEY` | ✅ | API-Key des Agents |

Credentials werden **nie** ins Image gebacken — immer als Laufzeit-Env-Vars übergeben.

## Portainer Stack

```yaml
services:
  pymon-agent:
    image: ghcr.io/mcfetz/pymon-agent:latest
    container_name: pymon-agent
    restart: unless-stopped
    environment:
      PYMON_SERVER:   "https://pymon.familie-heise.de/api"
      PYMON_AGENTID:  "my-host"
      PYMON_API_KEY:  "secret"
    volumes:
      - pymon-agent-plugins:/app/plugins
      - /var/run/docker.sock:/var/run/docker.sock
    pid: host
    network_mode: host

volumes:
  pymon-agent-plugins:
```

### Warum `pid: host` und `network_mode: host`?

| Einstellung | Zweck |
|-------------|-------|
| `pid: host` | psutil sieht alle Host-Prozesse → korrekte CPU/RAM/Disk-Werte |
| `network_mode: host` | Echte Netzwerk-Interfaces statt Container-Bridge + `NET_RAW` für ping |
| `/var/run/docker.sock` | docker_host-Plugin kann Docker-Metriken sammeln |

Ohne `pid: host` sieht psutil nur den Container-Namespace und liefert falsche Host-Werte.

## Manueller Redeploy

```bash
curl -fsS -X POST "<PORTAINER_WEBHOOK_URL>"
```
