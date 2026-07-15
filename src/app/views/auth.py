from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.exceptions import (
    AuthorIsBlockedError,
    AuthorNotFoundError,
    InvalidFormError,
    InvalidPasswordError,
    RefreshTokenExpiredError,
    RefreshTokenNotFoundError,
)
from app.models.author import Author
from app.models.refresh_token import RefreshToken
from app.serializers import AuthorSerializer, LoginSerializer, TokenRefreshSerializer
from app.utils.jwt import jwt_encode


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        methods=["POST"],
        request=LoginSerializer,
        tags=["Authentication"],
        auth=[],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            raise InvalidFormError(serializer)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            author = Author.objects.get_by_email(email)
        except Author.DoesNotExist as error:
            raise AuthorNotFoundError from error

        if not check_password(password, author.password):
            raise InvalidPasswordError

        if not author.active:
            raise AuthorIsBlockedError

        author.last_login = timezone.now()
        author.save()

        refresh_token = RefreshToken.objects.create(author=author)

        return Response(
            {
                "token": jwt_encode(
                    {
                        "id": author.id,
                        "name": author.name,
                        "email": author.email,
                    }
                ),
                "refresh_token": refresh_token.refresh_token,
            }
        )


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        methods=["POST"],
        request=TokenRefreshSerializer,
        tags=["Authentication"],
        auth=[],
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            raise InvalidFormError(serializer)

        refresh_token_value = serializer.validated_data["refresh_token"]

        try:
            refresh_token = RefreshToken.objects.get_by_refresh_token(refresh_token_value)
        except RefreshToken.DoesNotExist as error:
            raise RefreshTokenNotFoundError from error

        if refresh_token.expired_at < timezone.now():
            raise RefreshTokenExpiredError

        author = refresh_token.author
        if not author.active:
            raise AuthorIsBlockedError

        refresh_token = RefreshToken.objects.create(author=author)

        return Response(
            {
                "token": jwt_encode(
                    {
                        "id": author.id,
                        "name": author.name,
                        "email": author.email,
                    }
                ),
                "refresh_token": refresh_token.refresh_token,
            }
        )


class InfoView(APIView):
    @extend_schema(
        methods=["GET"],
        tags=["Authentication"],
    )
    def get(self, request):
        if not request.user.active:
            raise AuthorIsBlockedError

        serializer = AuthorSerializer(request.user)
        return Response(serializer.data)
