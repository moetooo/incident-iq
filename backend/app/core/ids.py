"""Identifier and fingerprint helpers."""

from __future__ import annotations

import hashlib
import uuid

ID_PREFIXES = {
    "incident": "inc_",
    "evidence": "ev_",
    "investigation": "inv_",
    "hypothesis": "hyp_",
    "remediation": "rem_",
    "audit": "aud_",
    "request": "req_",
    "step": "step_",
}


def new_id(entity: str) -> str:
    """Return a new opaque identifier for the given entity type."""
    prefix = ID_PREFIXES.get(entity, f"{entity}_")
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def fingerprint(*parts: object) -> str:
    """Return a stable SHA-256 digest over the given parts."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part if part is not None else "").strip().lower().encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()
