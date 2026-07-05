#!/usr/bin/env bash
# Arc — deploy or refresh the stack on a provisioned VPS, from your Mac.
#
#   deploy/remote-deploy.sh <server-ip> [ssh-user]
#
# It: waits for Docker on the box, clones (or pulls) the public repo, copies your
# local .env over (chmod 600, never committed), brings the stack up behind Caddy
# on <ip>.sslip.io with automatic HTTPS, then smoke-tests the public URL.
# Re-runnable: a second call pulls the latest commit and rebuilds.
set -euo pipefail

IP="${1:?usage: remote-deploy.sh <server-ip> [ssh-user]}"
SSH_USER="${2:-root}"
DOMAIN="${ARC_DOMAIN:-${IP}.sslip.io}"
REPO_URL="${ARC_REPO_URL:-https://github.com/aminssutt/Arc}"
REMOTE_DIR="${ARC_REMOTE_DIR:-/opt/arc}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
RSH() { ssh "${SSH_OPTS[@]}" "${SSH_USER}@${IP}" "$@"; }

[ -f .env ] || { echo "!! missing local .env (real keys live here) — create it first"; exit 1; }

echo ">> waiting for Docker on ${IP} (cloud-init may still be running) ..."
for _ in $(seq 1 60); do
  if RSH 'command -v docker >/dev/null && docker version >/dev/null 2>&1'; then
    echo "   docker is up"; break
  fi
  echo "   ... not ready, retrying in 10s"; sleep 10
done
RSH 'docker version >/dev/null 2>&1' || { echo "!! Docker never came up on ${IP}"; exit 1; }

echo ">> syncing the repo into ${REMOTE_DIR} ..."
RSH "set -e; if [ -d '${REMOTE_DIR}/.git' ]; then \
        git -C '${REMOTE_DIR}' fetch --depth 1 origin && \
        git -C '${REMOTE_DIR}' reset --hard origin/HEAD; \
     else \
        git clone --depth 1 '${REPO_URL}' '${REMOTE_DIR}'; \
     fi"

echo ">> copying local .env -> ${SSH_USER}@${IP}:${REMOTE_DIR}/.env (chmod 600) ..."
scp "${SSH_OPTS[@]}" .env "${SSH_USER}@${IP}:${REMOTE_DIR}/.env"
RSH "chmod 600 '${REMOTE_DIR}/.env'"

echo ">> building & starting the stack (ARC_DOMAIN=${DOMAIN}, ports 80/443) ..."
RSH "cd '${REMOTE_DIR}' && ARC_DOMAIN='${DOMAIN}' docker compose up -d --build"

echo ">> waiting for the public HTTPS endpoint (first-run cert issuance) ..."
OK=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 8 "https://${DOMAIN}/api/health" >/dev/null 2>&1; then OK=1; break; fi
  echo "   ... waiting for https://${DOMAIN} (cert + boot)"; sleep 6
done
[ "${OK}" = "1" ] || { echo "!! /api/health not reachable over HTTPS yet — check: RSH 'cd ${REMOTE_DIR} && docker compose logs caddy backend'"; exit 1; }

echo ">> smoke:"
echo -n "   /api/health : "; curl -fsS --max-time 8 "https://${DOMAIN}/api/health" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("200", d.get("status"), "agents=", ",".join(d.get("agents",{}).values()))'
LAND=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "https://${DOMAIN}/");        echo "   landing /    : ${LAND}"
MON=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "https://${DOMAIN}/monitor");   echo "   /monitor     : ${MON}"

cat << DONE

============================================================
  Arc is live:  https://${DOMAIN}
    landing        https://${DOMAIN}/
    control room   https://${DOMAIN}/monitor
    iOS app        point NEXT_PUBLIC/base URL at https://${DOMAIN}
  Rebuild : re-run this script (pulls latest + up --build)
  Logs    : ssh ${SSH_USER}@${IP} 'cd ${REMOTE_DIR} && docker compose logs -f'
============================================================
DONE
