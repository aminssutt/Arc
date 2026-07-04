#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_jwt(team_id: str, key_id: str, key_path: Path) -> str:
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("APNs auth key must be an EC private key")

    header = {"alg": "ES256", "kid": key_id}
    claims = {"iss": team_id, "iat": int(time.time())}
    signing_input = (
        f"{b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{b64url(json.dumps(claims, separators=(',', ':')).encode())}"
    )

    der_signature = private_key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der_signature)
    raw_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input}.{b64url(raw_signature)}"


def send_push(args: argparse.Namespace) -> None:
    load_env(Path(args.env_file))

    key_id = args.key_id or os.environ["APNS_KEY_ID"]
    team_id = args.team_id or os.environ["APNS_TEAM_ID"]
    bundle_id = args.bundle_id or os.environ.get("APNS_BUNDLE_ID", "com.arc.technician")
    device_token = args.device_token or os.environ["APNS_DEVICE_TOKEN"]
    key_path = Path(args.auth_key_path or os.environ["APNS_AUTH_KEY_PATH"]).expanduser()
    apns_env = args.apns_env or os.environ.get("APNS_ENV", "sandbox")
    payload_path = Path(args.payload)

    host = "api.push.apple.com" if apns_env == "production" else "api.sandbox.push.apple.com"
    url = f"https://{host}/3/device/{device_token}"
    token = make_jwt(team_id=team_id, key_id=key_id, key_path=key_path)

    payload = json.loads(payload_path.read_text())
    payload.pop("Simulator Target Bundle", None)

    headers = {
        "authorization": f"bearer {token}",
        "apns-topic": bundle_id,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }

    curl_headers = []
    for key, value in headers.items():
        curl_headers.extend(["-H", f"{key}: {value}"])

    result = subprocess.run(
        [
            "curl",
            "--http2",
            "-sS",
            "-D",
            "-",
            "-o",
            "-",
            "-X",
            "POST",
            *curl_headers,
            "--data-binary",
            json.dumps(payload, separators=(",", ":")),
            url,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0 or " 200 " not in result.stdout.splitlines()[0]:
        raise SystemExit(result.returncode or 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send an APNs alert push to ArcTechnician.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--payload", default="ios/Fixtures/sample_fault_push.apns")
    parser.add_argument("--key-id")
    parser.add_argument("--team-id")
    parser.add_argument("--bundle-id")
    parser.add_argument("--device-token")
    parser.add_argument("--auth-key-path")
    parser.add_argument("--apns-env", choices=["sandbox", "production"])
    return parser.parse_args()


if __name__ == "__main__":
    send_push(parse_args())
