"""Deploy keys for agent credentials.

The backend creates an ed25519 key pair, keeps only the OpenSSH public key and
throws the private key away: in the demo the deploy key is the agent's
identity on GitHub, not something anyone logs in with.
"""
from __future__ import annotations

import hashlib


def generate_public_key(comment: str) -> str:
    # Imported lazily so the rest of the backend runs without cryptography.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode("ascii")
    return f"{public_key} {comment}"


def key_title(resource_key: str, idempotency_key: str) -> str:
    """Stable title, so n8n can skip a key it already added on a retry and the
    verifier can find the key without trusting n8n's response."""
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:10]
    return f"livingops:{resource_key}:{digest}"[:100]
