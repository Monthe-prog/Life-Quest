from __future__ import annotations

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, hash_token, verify_password


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("Password12345")

    assert password_hash != "Password12345"
    assert verify_password("Password12345", password_hash)
    assert not verify_password("WrongPassword12345", password_hash)


def test_access_token_contains_expected_claims() -> None:
    token = create_access_token("user-123")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["jti"]
    assert payload["exp"] > payload["iat"]


def test_refresh_token_can_use_explicit_jti() -> None:
    token = create_refresh_token("user-123", token_id="refresh-id")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert payload["jti"] == "refresh-id"


def test_hash_token_is_stable_sha256() -> None:
    digest = hash_token("token-value")

    assert digest == hash_token("token-value")
    assert len(digest) == 64
