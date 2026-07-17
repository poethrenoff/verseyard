from django.conf import settings
from pgvector.django import CosineDistance

from app.models.poem import Poem
from app.models.poem_embedding import PoemEmbedding


def anti_repeat_score(poem: Poem) -> int | None:
    """Маппинг близости к корпусу автора в шкалу anti_repeat (0–10).

    Чем ближе стих к уже написанным (выше cosine similarity), тем НИЖЕ балл:
    повтор — это хуже. Возвращает None, если эмбеддинг ещё не посчитан.
    """
    target = PoemEmbedding.objects.filter(poem=poem).first()
    if target is None:
        return None

    nearest = (
        PoemEmbedding.objects.filter(poem__author=poem.author, poem__active=True)
        .exclude(poem_id=poem.id)
        .annotate(distance=CosineDistance("vector", target.vector))
        .order_by("distance")
        .first()
    )
    if nearest is None:
        return 10

    similarity = 1 - nearest.distance
    return int(max(0, min(10, round((1 - similarity) * 10))))
