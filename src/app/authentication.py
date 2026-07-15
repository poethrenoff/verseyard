import re

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from jwt.exceptions import PyJWTError
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from app.exceptions import (
    AuthorImpersonationError,
    AuthorIsBlockedError,
    AuthorNotFoundError,
    InvalidJWTTokenError,
)
from app.models.author import Author
from app.utils.jwt import jwt_decode


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "app.authentication.JWTAuthentication"
    name = "bearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "JWT Token in format: Bearer <token>",
        }


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        authorization = request.headers.get("authorization")
        if not authorization:
            return None

        token = re.sub(r"^Bearer\s+", "", authorization, flags=re.IGNORECASE)

        try:
            payload = jwt_decode(token)
        except (PyJWTError, ValueError) as error:
            raise InvalidJWTTokenError from error

        try:
            author = Author.objects.get_by_user_id(payload["id"])
        except Author.DoesNotExist as error:
            raise AuthorNotFoundError from error

        switch_user = request.headers.get("x-switch-user")
        if switch_user:
            if not author.can_switch_user:
                raise AuthorImpersonationError

            try:
                author = Author.objects.get_by_email(switch_user)
            except Author.DoesNotExist as error:
                raise AuthorNotFoundError from error

        if not author.active:
            raise AuthorIsBlockedError

        return author, token


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if not isinstance(request.user, Author):
            raise InvalidJWTTokenError

        return True
