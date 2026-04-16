"""T152: Tiny FastAPI mock for WordPress JWKS + token issuance — offline dev/testing only.

Usage:
    uvicorn app.scripts.wp_mock:app --port 8001

Exposes:
    GET  /.well-known/jwks.json   → JWKS with one RSA key
    POST /wp-json/jwt-auth/v1/token  → Issue a signed WP-style JWT
"""
import time
import uuid

from fastapi import FastAPI
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose import jwt, jwk

app = FastAPI(title="WP Auth Mock", version="0.1.0")

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_kid = "wp-mock-key-1"

_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

_public_jwk = jwk.RSAKey(algorithm="RS256", key=_public_pem.decode()).to_dict()
_public_jwk["kid"] = _kid
_public_jwk["use"] = "sig"

_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


@app.get("/.well-known/jwks.json")
async def jwks():
    return {"keys": [_public_jwk]}


@app.post("/wp-json/jwt-auth/v1/token")
async def issue_token(
    wp_user_id: int = 42,
    email: str = "test@aueshah.com",
    display_name: str = "Test User",
):
    now = int(time.time())
    payload = {
        "iss": "http://localhost:8001",
        "iat": now,
        "exp": now + 3600,
        "sub": wp_user_id,
        "email": email,
        "display_name": display_name,
        "data": {
            "user": {
                "id": wp_user_id,
                "email": email,
                "display_name": display_name,
            }
        },
    }
    token = jwt.encode(payload, _private_pem.decode(), algorithm="RS256", headers={"kid": _kid})
    return {"token": token, "user_email": email, "user_display_name": display_name}
