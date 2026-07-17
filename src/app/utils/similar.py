from django.conf import settings
from pgvector.django import CosineDistance

from app.models.poem import Poem
from app.models.poem_embedding import PoemEmbedding

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    vectors = get_model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        processing_kwargs={"text": {"max_length": 512, "truncation": True}},
    )
    return [vector.tolist() for vector in vectors]


def find_similar(poem: Poem) -> list[dict]:
    target = PoemEmbedding.objects.filter(poem=poem).first()
    if target is None:
        return []

    candidates = (
        PoemEmbedding.objects.filter(poem__author=poem.author, poem__active=True)
        .exclude(poem_id=poem.id)
        .annotate(distance=CosineDistance("vector", target.vector))
        .order_by("distance")[: settings.SIMILARITY_LIMIT]
    )

    results = []
    for candidate in candidates:
        similarity = 1 - candidate.distance
        if similarity < settings.SIMILARITY_THRESHOLD:
            continue
        results.append(
            {
                "id": candidate.poem_id,
                "title": candidate.poem.title,
                "comment": candidate.poem.comment,
                "similarity": round(similarity, 4),
            }
        )

    return results
