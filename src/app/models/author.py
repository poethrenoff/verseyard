from django.db import models


class AuthorManager(models.Manager):
    def get_by_user_id(self, user_id: int):
        return self.get(pk=user_id)

    def get_by_email(self, email: str):
        return self.get(email__iexact=email)


class Author(models.Model):
    name = models.CharField()
    email = models.EmailField(unique=True)
    password = models.CharField()

    last_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    can_switch_user = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    objects = AuthorManager()

    def __str__(self) -> str:
        return f"{self.email}"
