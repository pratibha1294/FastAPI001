import time
from datetime import datetime, timedelta, timezone

import pytest

from jwt import (
    TokenData,
    TokenIsExpiredError,
    TokenIsInvalidError,
    validate,
    create,
)


def test_encrypt_returns_a_string():
    token = create(sub="user-1")
    assert isinstance(token, str)
    assert token.count(".") == 2


def test_decrypt_returns_token_data_with_defaults():
    token = create(sub="user-1")
    data = validate(token)

    assert isinstance(data, TokenData)
    assert data.sub == "user-1"
    assert data.claims == {}
    assert isinstance(data.iat, datetime)
    assert isinstance(data.exp, datetime)
    assert data.exp > data.iat


def test_encrypt_with_custom_claims_and_exp():
    exp = datetime.now(timezone.utc) + timedelta(hours=2)
    token = create(sub="user-2", claims={"role": "admin"}, exp=exp)
    data = validate(token)

    assert data.sub == "user-2"
    assert data.claims == {"role": "admin"}
    assert data.exp.replace(microsecond=0) == exp.replace(microsecond=0)


def test_decrypt_expired_token_raises_token_is_expired_error():
    exp = datetime.now(timezone.utc) - timedelta(seconds=1)
    token = create(sub="user-3", exp=exp)

    with pytest.raises(TokenIsExpiredError):
        validate(token)


def test_decrypt_malformed_token_raises_token_is_invalid_error():
    with pytest.raises(TokenIsInvalidError):
        validate("not-a-valid-jwt")


def test_decrypt_tampered_signature_raises_token_is_invalid_error():
    token = create(sub="user-4", secret="secret-a")

    with pytest.raises(TokenIsInvalidError):
        validate(token, secret="secret-b")
