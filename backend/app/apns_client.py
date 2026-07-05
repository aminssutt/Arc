"""Real APNs sender (INT.7) — token-based ES256 auth over HTTP/2.

Signs a short-lived provider JWT (ES256) with the Apple team key and POSTs the
push payload to Apple's sandbox gateway over HTTP/2. Imports are lazy (PyJWT +
httpx[http2]), so a backend running push_mode=file/simctl never needs the Apple
dependencies. No token, key, or signed JWT is ever logged.
"""
import logging
import time

logger = logging.getLogger("arc.apns")

_SANDBOX_HOST = "api.sandbox.push.apple.com"
_PROD_HOST = "api.push.apple.com"
_ARMOR_BEGIN = "-----BEGIN PRIVATE KEY-----"
_ARMOR_END = "-----END PRIVATE KEY-----"


def normalize_pem(raw: str) -> str:
    """Coerce whatever .env stores into a PEM cryptography/PyJWT can load.

    Accepts an armored multi-line PEM, an armored PEM with literal ``\\n``
    escapes, or a bare base64 PKCS#8 body (no armor), and returns a standard
    armored PEM with real newlines.
    """
    text = (raw or "").strip()
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")
    if _ARMOR_BEGIN in text:
        return text.strip() + "\n"
    body = "".join(text.split())  # bare base64 -> wrap in armor, 64-char lines
    wrapped = "\n".join(body[i:i + 64] for i in range(0, len(body), 64))
    return f"{_ARMOR_BEGIN}\n{wrapped}\n{_ARMOR_END}\n"


class ApnsError(RuntimeError):
    pass


class ApnsClient:
    """Token-based APNs client. Constructing it validates the signing key."""

    def __init__(self, team_id: str, key_id: str, private_key_pem: str,
                 bundle_id: str, *, use_sandbox: bool = True,
                 token_ttl_s: int = 3000) -> None:
        if not (team_id and key_id and private_key_pem):
            raise ApnsError("APNs not configured (team_id, key_id and private key required)")
        self.team_id = team_id
        self.key_id = key_id
        self.bundle_id = bundle_id
        self.host = _SANDBOX_HOST if use_sandbox else _PROD_HOST
        self._pem = normalize_pem(private_key_pem)
        self._token_ttl_s = token_ttl_s
        self._jwt: str | None = None
        self._jwt_iat = 0
        self._provider_token(force=True)  # fail fast on a bogus/placeholder key

    def _provider_token(self, *, force: bool = False) -> str:
        import jwt  # lazy: only needed on the real APNs path
        now = int(time.time())
        if not force and self._jwt and (now - self._jwt_iat) < self._token_ttl_s:
            return self._jwt
        token = jwt.encode(
            {"iss": self.team_id, "iat": now},
            self._pem,
            algorithm="ES256",
            headers={"alg": "ES256", "kid": self.key_id},
        )
        self._jwt, self._jwt_iat = token, now
        return token

    def build_headers(self, *, priority: int = 10, collapse_id: str | None = None) -> dict[str, str]:
        headers = {
            "authorization": f"bearer {self._provider_token()}",
            "apns-topic": self.bundle_id,
            "apns-push-type": "alert",
            "apns-priority": str(priority),
        }
        if collapse_id:
            headers["apns-collapse-id"] = collapse_id[:64]
        return headers

    @staticmethod
    def apns_body(payload: dict) -> dict:
        """The APNs JSON body: the push payload minus the simctl-only helper key."""
        return {k: v for k, v in payload.items() if k != "Simulator Target Bundle"}

    async def send(self, device_token: str, payload: dict, *,
                   collapse_id: str | None = None) -> tuple[bool, int, str]:
        """POST the payload to one device token. Returns (ok, status, reason)."""
        import httpx  # lazy
        url = f"https://{self.host}/3/device/{device_token}"
        try:
            headers = self.build_headers(collapse_id=collapse_id)
            async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
                resp = await client.post(url, json=self.apns_body(payload), headers=headers)
        except Exception as exc:  # noqa: BLE001 - network/TLS/HTTP2/signing failure, never fatal
            return (False, 0, f"{exc.__class__.__name__}")
        if resp.status_code == 200:
            return (True, 200, "ok")
        try:
            reason = resp.json().get("reason", "")
        except Exception:  # noqa: BLE001
            reason = resp.text[:120]
        return (False, resp.status_code, reason)
