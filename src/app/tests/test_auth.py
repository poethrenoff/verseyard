from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from app.models.author import Author
from app.models.refresh_token import RefreshToken
from app.utils.jwt import jwt_encode


class AuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "secret123"
        self.author = Author.objects.create(
            name="Test Author",
            email="test@example.com",
            password=make_password(self.password),
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login/", {"email": "test@example.com", "password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("refresh_token", data)

        # Verify refresh token was created in DB
        self.assertTrue(RefreshToken.objects.filter(author=self.author).exists())

    def test_login_invalid_password(self):
        response = self.client.post(
            "/api/auth/login/", {"email": "test@example.com", "password": "wrongpassword"}, format="json"
        )

        # APIError handling might return 401 based on InvalidPasswordError
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "InvalidPasswordError")

    def test_login_blocked(self):
        self.author.active = False
        self.author.save()

        response = self.client.post(
            "/api/auth/login/", {"email": "test@example.com", "password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["type"], "AuthorIsBlockedError")

    def test_login_not_found(self):
        response = self.client.post(
            "/api/auth/login/", {"email": "nonexistent@example.com", "password": "password"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["type"], "AuthorNotFoundError")

    def test_token_refresh_success(self):
        refresh_token = RefreshToken.objects.create(author=self.author)

        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh_token": refresh_token.refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("refresh_token", data)

    def test_token_refresh_expired(self):
        refresh_token = RefreshToken.objects.create(author=self.author)
        refresh_token.expired_at = timezone.now() - timedelta(seconds=1)
        refresh_token.save()

        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh_token": refresh_token.refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "RefreshTokenExpiredError")

    def test_token_refresh_blocked(self):
        refresh_token = RefreshToken.objects.create(author=self.author)
        self.author.active = False
        self.author.save()

        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh_token": refresh_token.refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["type"], "AuthorIsBlockedError")

    def test_token_refresh_not_found(self):
        response = self.client.post("/api/auth/token/refresh/", {"refresh_token": "nonexistent_token"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["type"], "RefreshTokenNotFoundError")

    def test_info_success(self):
        login_response = self.client.post(
            "/api/auth/login/", {"email": "test@example.com", "password": self.password}, format="json"
        )
        token = login_response.json()["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/auth/info/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["name"], "Test Author")

    def test_info_blocked(self):
        self.author.active = False
        self.author.save()

        refresh_token = RefreshToken.objects.create(author=self.author)
        token = jwt_encode({"id": self.author.id, "name": self.author.name, "email": self.author.email})

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/auth/info/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["type"], "AuthorIsBlockedError")

    def test_info_unauthorized(self):
        response = self.client.get("/api/auth/info/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "InvalidJWTTokenError")
