#!/usr/bin/env bash
# Arc — provision ONE Vultr VPS for the demo (Vultr API v2).
#
# Requires: curl, python3, and VULTR_ACCOUNT_API_KEY (Vultr *control-plane* API
# key — NOT the inference key). Creates an Ubuntu 24.04 instance (vc2-2c-4gb) in
# an EU region, tagged "arc-demo", with Docker + the compose plugin installed via
# cloud-init. Idempotent: if an "arc-demo" instance already exists it prints its
# IP and exits instead of creating a second one.
#
#   VULTR_ACCOUNT_API_KEY=... deploy/provision.sh
#
# Then:  deploy/remote-deploy.sh <printed-ip>
set -euo pipefail

API="https://api.vultr.com/v2"
LABEL="${ARC_INSTANCE_LABEL:-arc-demo}"
TAG="arc-demo"
PLAN="${ARC_PLAN:-vc2-2c-4gb}"
OS_NAME="${ARC_OS_NAME:-Ubuntu 24.04 LTS x64}"
REGION_PREF="${ARC_REGION_PREF:-cdg fra ams lhr}"   # Paris, Frankfurt, Amsterdam, London

: "${VULTR_ACCOUNT_API_KEY:?set VULTR_ACCOUNT_API_KEY (Vultr control-plane API key)}"
command -v curl    >/dev/null || { echo "curl is required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

AUTH=(-H "Authorization: Bearer ${VULTR_ACCOUNT_API_KEY}" -H "Content-Type: application/json")
api() { curl -fsS "${AUTH[@]}" "$@"; }
# pyq <json-on-stdin> <python-expr over `d`> — tiny JSON query helper.
pyq() { python3 -c 'import sys,json; d=json.load(sys.stdin); print(eval(sys.argv[1]))' "$1"; }

echo ">> checking for an existing '${LABEL}' instance ..."
EXISTING=$(api "${API}/instances?per_page=500" | python3 -c '
import sys, json
d = json.load(sys.stdin)
lab = sys.argv[1]
for i in d.get("instances", []):
    if i.get("label") == lab:
        print(i["id"], i.get("main_ip", "0.0.0.0")); break
' "${LABEL}" || true)
if [ -n "${EXISTING}" ]; then
  ID=$(echo "${EXISTING}" | awk '{print $1}')
  IP=$(echo "${EXISTING}" | awk '{print $2}')
  echo "!! '${LABEL}' already exists (id=${ID}, ip=${IP}). Refusing to duplicate."
  echo "   Deploy with: deploy/remote-deploy.sh ${IP}"
  echo "   Destroy with: curl -X DELETE ${API}/instances/${ID} -H 'Authorization: Bearer \$VULTR_ACCOUNT_API_KEY'"
  exit 0
fi

echo ">> resolving os_id for '${OS_NAME}' ..."
OS_ID=$(api "${API}/os?per_page=500" | python3 -c '
import sys, json
d = json.load(sys.stdin)
want = sys.argv[1]
for o in d.get("os", []):
    if o.get("name") == want:
        print(o["id"]); break
' "${OS_NAME}")
[ -n "${OS_ID}" ] || { echo "could not find os '${OS_NAME}'"; exit 1; }
echo "   os_id=${OS_ID}"

echo ">> picking an EU region where ${PLAN} is available ..."
REGIONS_JSON=$(api "${API}/regions?per_page=500")
PLAN_REGIONS=$(api "${API}/plans?type=vc2&per_page=500" | python3 -c '
import sys, json
d = json.load(sys.stdin); plan = sys.argv[1]
for p in d.get("plans", []):
    if p.get("id") == plan:
        print(" ".join(p.get("locations", []))); break
' "${PLAN}")
REGION=$(python3 -c '
import sys, json
regions = json.loads(sys.argv[1]).get("regions", [])
avail   = set(sys.argv[2].split())
pref    = sys.argv[3].split()
by_id   = {r["id"]: r for r in regions}
# 1) preference list, restricted to regions that offer the plan
for rid in pref:
    if rid in by_id and (not avail or rid in avail):
        print(rid); sys.exit()
# 2) any European region that offers the plan
for r in regions:
    if r.get("continent") == "Europe" and (not avail or r["id"] in avail):
        print(r["id"]); sys.exit()
# 3) last resort: first region offering the plan
for r in regions:
    if not avail or r["id"] in avail:
        print(r["id"]); sys.exit()
' "${REGIONS_JSON}" "${PLAN_REGIONS}" "${REGION_PREF}")
[ -n "${REGION}" ] || { echo "no region offers ${PLAN}"; exit 1; }
echo "   region=${REGION}"

# cloud-init: install Docker (+ compose plugin) so remote-deploy can just build.
read -r -d '' CLOUD_INIT << 'CI' || true
#cloud-config
package_update: true
packages: [ca-certificates, curl, git]
runcmd:
  - curl -fsSL https://get.docker.com | sh
  - systemctl enable --now docker
  - touch /root/.arc-provisioned
CI
USER_DATA_B64=$(printf '%s' "${CLOUD_INIT}" | base64 | tr -d '\n')

echo ">> creating instance (label=${LABEL}, plan=${PLAN}, region=${REGION}) ..."
BODY=$(python3 -c '
import json, sys
print(json.dumps({
    "region": sys.argv[1], "plan": sys.argv[2], "os_id": int(sys.argv[3]),
    "label": sys.argv[4], "hostname": sys.argv[4],
    "tags": [sys.argv[5]], "user_data": sys.argv[6], "backups": "disabled",
}))
' "${REGION}" "${PLAN}" "${OS_ID}" "${LABEL}" "${TAG}" "${USER_DATA_B64}")
CREATE=$(api -X POST "${API}/instances" -d "${BODY}")
ID=$(echo "${CREATE}" | pyq 'd["instance"]["id"]')
echo "   instance id=${ID}"

echo ">> waiting for a public IP (this takes ~1-2 min) ..."
IP="0.0.0.0"
for _ in $(seq 1 40); do
  sleep 10
  INFO=$(api "${API}/instances/${ID}")
  IP=$(echo "${INFO}" | pyq 'd["instance"].get("main_ip","0.0.0.0")')
  ST=$(echo "${INFO}" | pyq 'd["instance"].get("server_status","")')
  echo "   ... ip=${IP} status=${ST}"
  [ "${IP}" != "0.0.0.0" ] && break
done
[ "${IP}" != "0.0.0.0" ] || { echo "timed out waiting for IP (instance id=${ID})"; exit 1; }

cat << DONE

============================================================
  Arc VPS ready
    id     : ${ID}
    ip     : ${IP}
    domain : ${IP}.sslip.io   (HTTPS via Let's Encrypt)
  Next:
    deploy/remote-deploy.sh ${IP}
  Destroy later:
    curl -X DELETE ${API}/instances/${ID} \\
      -H "Authorization: Bearer \$VULTR_ACCOUNT_API_KEY"
============================================================
DONE
