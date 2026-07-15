from django.db import models


class Collection(models.Model):
    author = models.ForeignKey(
        "app.Author",
        on_delete=models.PROTECT,
        related_name="collections",
    )
    title = models.CharField(max_length=255)
    comment = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title}"
