from datetime import timedelta
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task
def refresh_token_cleanup() -> None:
    from app.models.refresh_token import RefreshToken

    RefreshToken.objects.filter(
        created_at__lte=timezone.now() - timedelta(seconds=settings.REFRESH_TOKEN_EXPIRES)
    ).delete()


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=30,
)
def assess_poem(poem_id: int) -> dict[str, dict[str, Any] | Any]:
    from app.models.assessment import PoemAssessment
    from app.models.poem import Poem
    from app.utils.assessment import anti_repeat_score
    from app.utils.llm import assess

    poem = Poem.objects.get(id=poem_id)

    scores = assess(poem.content)
    scores["anti_repeat"] = anti_repeat_score(poem)
    scores["model_name"] = settings.LLM_MODEL_NAME or ""

    PoemAssessment.objects.update_or_create(poem=poem, defaults=scores)

    return {
        "scores": {
            "freshness": scores["freshness"],
            "emotional_density": scores["emotional_density"],
            "voice": scores["voice"],
            "completeness": scores["completeness"],
            "anti_repeat": scores["anti_repeat"],
        },
        "comment": scores["comment"],
        "model_name": scores["model_name"],
    }


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=10,
)
def embed_poem(poem_id: int) -> None:
    from app.models.poem import Poem
    from app.models.poem_embedding import PoemEmbedding

    poem = Poem.objects.get(id=poem_id)
    from app.utils.fence import encode

    (vector,) = encode([poem.content])

    PoemEmbedding.objects.update_or_create(
        poem=poem,
        defaults={"vector": vector, "model_name": settings.EMBEDDING_MODEL_NAME},
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=15,
    default_retry_delay=2,
)
def compute_poem_similarity(self, poem_id: int):
    from app.models.poem import Poem
    from app.models.poem_embedding import PoemEmbedding
    from app.utils.fence import find_similar

    poem = Poem.objects.get(id=poem_id)

    if not PoemEmbedding.objects.filter(poem_id=poem.id).exists():
        raise self.retry(exc=Exception("Embedding not ready"), countdown=2)

    return find_similar(poem)
