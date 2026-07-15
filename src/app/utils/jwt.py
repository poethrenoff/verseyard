from datetime import timedelta

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.utils import timezone


def jwt_encode(payload: dict) -> str:
    payload["iat"] = timezone.now()
    payload["exp"] = timezone.now() + timedelta(seconds=settings.JWT_TOKEN_TTL)

    private_key = serialization.load_pem_private_key(
        settings.JWT_PRIVATE_KEY.encode(),
        password=settings.JWT_PASSPHRASE.encode(),
        backend=default_backend(),
    )

    return jwt.encode(payload, private_key, algorithm="RS256")


def jwt_decode(token: str) -> dict:
    public_key = serialization.load_pem_public_key(settings.JWT_PUBLIC_KEY.encode())

    return jwt.decode(token, public_key, algorithms=["RS256"], options={"require": ["iat", "exp"]})
