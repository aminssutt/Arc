# Arc — Deploy

The whole stack ships as three containers behind one reverse proxy. **Only Caddy
binds host ports**, so there is never a port clash on the box; the browser (and
the iPhone) talk to a single HTTPS origin and Caddy routes `/api/*` to the
backend and everything else to the Next.js control room.

```
[ browser / iPhone ] --HTTPS--> [ caddy ] --/api/*--> [ backend :8000 (FastAPI) ]
                                          \--else----> [ frontend :3000 (Next.js) ]
```

## Three commands

```bash
# 1. Provision a Vultr VPS (Ubuntu 24.04, docker preinstalled). Prints the IP.
VULTR_ACCOUNT_API_KEY=xxxxx deploy/provision.sh

# 2. Build + start the stack on that box, with automatic HTTPS on <ip>.sslip.io.
deploy/remote-deploy.sh <printed-ip>

# 3. Point the iOS app's backend base URL at:
https://<ip>.sslip.io
```

`remote-deploy.sh` clones the public repo on the server, copies your **local
`.env`** over (chmod 600 — real keys never leave your machine via git), runs
`docker compose up -d --build`, and smoke-tests `https://<ip>.sslip.io/api/health`.

## Environment variables

| Var | Where | Default | Role |
|---|---|---|---|
| `ARC_DOMAIN` | compose/Caddy | `localhost` | Real hostname → Let's Encrypt HTTPS; `localhost` → self-signed |
| `HTTP_PORT` / `HTTPS_PORT` | compose | `80` / `443` | Host ports Caddy binds (change for a local run) |
| `NEXT_PUBLIC_ARC_BACKEND_URL` | frontend build arg | *(empty)* | Empty = same-origin via proxy (portable image); set only to bypass the proxy |
| `VULTR_ACCOUNT_API_KEY` | provision.sh | — | Vultr **control-plane** key (not the inference key) |
| `ARC_REPO_URL` | remote-deploy.sh | `github.com/aminssutt/Arc` | Repo cloned on the box |
| everything in `.env` | backend `env_file` | — | Vultr inference + APNs keys, push mode, … |

Backend push-out and the iPhone device registry are redirected onto the
**named volume `arc-runtime`** (`ARC_PUSH_OUT_DIR=/var/lib/arc/push-out`,
`ARC_DEVICE_STORE=/var/lib/arc/push-out/devices.runtime.json`), so registered
tokens survive restarts. Caddy certs persist in the `caddy-data` volume.

## Run it locally (no VPS)

```bash
HTTP_PORT=8080 HTTPS_PORT=8443 docker compose up -d --build
curl -k https://localhost:8443/api/health      # backend, real agents if .env present
open https://localhost:8443/                    # landing (accept the self-signed cert)
```

## Rebuild after a code change

```bash
deploy/remote-deploy.sh <ip>        # remote: pulls latest, rebuilds, restarts
docker compose up -d --build        # local
```

## Tear everything down

```bash
docker compose down -v              # stop + drop volumes (local or on the box)

# Destroy the VPS (id printed by provision.sh):
curl -X DELETE https://api.vultr.com/v2/instances/<id> \
  -H "Authorization: Bearer $VULTR_ACCOUNT_API_KEY"
```
