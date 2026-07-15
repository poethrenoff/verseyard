from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from app.settings import REFRESH_TOKEN_EXPIRES


@shared_task
def refresh_token_cleanup() -> None:
    from app.models.refresh_token import RefreshToken

    RefreshToken.objects.filter(created_at__lte=timezone.now() - timedelta(seconds=REFRESH_TOKEN_EXPIRES)).delete()
