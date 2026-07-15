import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from app.settings import REFRESH_TOKEN_EXPIRES


class RefreshTokenManager(models.Manager):
    def get_by_refresh_token(self, refresh_token: str):
        return self.get(refresh_token=refresh_token)


class RefreshToken(models.Model):
    author = models.ForeignKey("app.Author", on_delete=models.CASCADE)
    refresh_token = models.CharField(db_index=True)
    expired_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = RefreshTokenManager()

    class Meta:
        db_table = "app_refresh_token"

    def save(self, *args, **kwargs):
        if not self.refresh_token:
            self.set_refresh_token()

        super().save(*args, **kwargs)

    def set_refresh_token(self):
        while True:
            self.refresh_token = secrets.token_hex(64)
            if not RefreshToken.objects.filter(refresh_token=self.refresh_token).exists():
                self.expired_at = timezone.now() + timedelta(seconds=REFRESH_TOKEN_EXPIRES)
                break
