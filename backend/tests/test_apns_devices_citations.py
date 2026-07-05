"""INT.7 + DEMO.1 acceptance: multi-line .env PEM parsing, ES256 APNs signing,
the device-token registry + POST /api/devices, and GET /api/citations.
All offline — a real EC key is generated in-process; no network is touched.
"""
import base64
import os

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient

from backend.app.apns_client import ApnsClient, normalize_pem
from backend.app.device_store import DeviceStore
from backend.app.main import create_app
from backend.app.settings import _load_dotenv


@pytest.fixture()
async def client():
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.app = app
            yield c


def _ec_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption()).decode()


# -- .env multi-line quoted value parsing (the APPLE_PRIVATE_KEY_PEM case) -----
def test_load_dotenv_parses_multiline_quoted_pem(tmp_path):
    pem = _ec_pem().strip()
    env = tmp_path / ".env"
    env.write_text(
        'MLTEST_NORMAL=simplevalue\n'
        f'MLTEST_PEM="{pem}"\n'
        'MLTEST_AFTER=after\n',
        encoding="utf-8")
    for k in ("MLTEST_NORMAL", "MLTEST_PEM", "MLTEST_AFTER"):
        os.environ.pop(k, None)
    try:
        _load_dotenv(env)
        assert os.environ["MLTEST_NORMAL"] == "simplevalue"
        assert os.environ["MLTEST_AFTER"] == "after"          # parser resumed after the block
        loaded = os.environ["MLTEST_PEM"]
        assert loaded == pem                                   # real newlines preserved verbatim
        assert "\n" in loaded and loaded.startswith("-----BEGIN")
    finally:
        for k in ("MLTEST_NORMAL", "MLTEST_PEM", "MLTEST_AFTER"):
            os.environ.pop(k, None)


def test_load_dotenv_single_line_unchanged(tmp_path):
    env = tmp_path / ".env"
    env.write_text('SL_PLAIN=abc\nSL_QUOTED="def"\n', encoding="utf-8")
    for k in ("SL_PLAIN", "SL_QUOTED"):
        os.environ.pop(k, None)
    try:
        _load_dotenv(env)
        assert os.environ["SL_PLAIN"] == "abc"
        assert os.environ["SL_QUOTED"] == "def"                # outer quotes stripped, as before
    finally:
        for k in ("SL_PLAIN", "SL_QUOTED"):
            os.environ.pop(k, None)


# -- normalize_pem: armored / bare-base64 both load ----------------------------
def test_normalize_pem_variants_load_for_es256():
    pem = _ec_pem()
    der = serialization.load_pem_private_key(pem.encode(), password=None).private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    bare_b64 = base64.b64encode(der).decode()
    armored = normalize_pem(bare_b64)
    assert "-----BEGIN PRIVATE KEY-----" in armored and "-----END PRIVATE KEY-----" in armored
    # both the armored-from-bare and the escaped-\n form load as a usable key
    serialization.load_pem_private_key(armored.encode(), password=None)
    escaped = normalize_pem(pem.replace("\n", "\\n"))
    serialization.load_pem_private_key(escaped.encode(), password=None)


# -- ApnsClient signs a valid ES256 provider JWT -------------------------------
def test_apns_client_signs_verifiable_es256_token():
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    c = ApnsClient("TEAM123456", "KEYA123456", pem, "com.arc.operator", use_sandbox=True)
    assert c.host == "api.sandbox.push.apple.com"
    token = c._provider_token(force=True)
    decoded = jwt.decode(token, key.public_key(), algorithms=["ES256"])
    header = jwt.get_unverified_header(token)
    assert decoded["iss"] == "TEAM123456" and "iat" in decoded
    assert header["kid"] == "KEYA123456" and header["alg"] == "ES256"
    # apns body drops the simctl-only helper key
    assert "Simulator Target Bundle" not in ApnsClient.apns_body(
        {"Simulator Target Bundle": "x", "aps": {}})


def test_apns_client_accepts_bare_base64_key():
    pem = _ec_pem()
    der = serialization.load_pem_private_key(pem.encode(), password=None).private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    ApnsClient("T1234567890", "K1234567890", base64.b64encode(der).decode(),
               "com.arc.operator")  # constructs (signs) without raising


def test_apns_client_rejects_bogus_key():
    with pytest.raises(Exception):
        ApnsClient("T", "K", "not-a-real-key", "com.arc.operator")


# -- Device-token registry: register, persist, reload --------------------------
def test_device_store_register_persist_reload(tmp_path):
    path = tmp_path / "devices.runtime.json"
    store = DeviceStore(path)
    store.register("tok-aaa", platform="ios", operator_id="EMP-001")
    store.register("tok-bbb", platform="ios", operator_id="EMP-002")
    store.register("tok-ccc", platform="ios", operator_id=None)
    assert store.tokens_for("EMP-001") == ["tok-aaa"]
    assert store.tokens_for("EMP-999") == []                 # unknown operator
    assert set(store.all_tokens()) == {"tok-aaa", "tok-bbb", "tok-ccc"}
    # survives a reload (new instance reads the .runtime file)
    reloaded = DeviceStore(path)
    assert reloaded.tokens_for("EMP-001") == ["tok-aaa"]
    assert reloaded.count() == 3


# -- POST /api/devices ---------------------------------------------------------
async def test_post_devices_registers_token(client):
    r = await client.post("/api/devices", json={
        "device_token": "APNS-DEVICE-TOKEN-XYZ", "platform": "ios", "operator_id": "EMP-001"})
    assert r.status_code == 204
    assert "APNS-DEVICE-TOKEN-XYZ" in client.app.state.device_store.tokens_for("EMP-001")


async def test_post_devices_requires_token(client):
    r = await client.post("/api/devices", json={"platform": "ios"})
    assert r.status_code == 422


# -- GET /api/citations --------------------------------------------------------
async def test_citations_resolves_known_doc(client):
    r = await client.get("/api/citations/V4", params={"claim": "rectifier-lost alarm signature"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["doc_id"] == "V4" and body["title"]
    assert body["snippet"]                                    # a real excerpt from the source
    assert body["source_path"].endswith("v4_netsure2100.pdf")
    assert {"doc_id", "title", "section", "snippet", "source_path"} <= set(body)


async def test_citations_unknown_doc_is_404(client):
    r = await client.get("/api/citations/DOES-NOT-EXIST", params={"claim": "x"})
    assert r.status_code == 404


async def test_citations_serves_inline_text_doc(client):
    # O5 has path=null + an inline `text` field (link-only spare listing) -> 200
    r = await client.get("/api/citations/O5", params={"claim": "APR48-3G price"})
    assert r.status_code == 200, r.text
    assert r.json()["doc_id"] == "O5" and r.json()["snippet"]


async def test_citations_pivot_docs_resolve(client):
    # the pivot cites S2 (measurement point failure) + V2 (supervision module)
    for doc_id, claim in [("S2", "measurement point failure"), ("V2", "supervision module")]:
        r = await client.get(f"/api/citations/{doc_id}", params={"claim": claim})
        assert r.status_code == 200, r.text
        assert r.json()["snippet"]
