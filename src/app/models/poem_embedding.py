from django.db import models
from pgvector.django import HnswIndex, VectorField


class PoemEmbedding(models.Model):
    poem = models.OneToOneField(
        "app.Poem",
        on_delete=models.CASCADE,
        related_name="embedding",
    )
    vector = VectorField(dimensions=1024)
    model_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_poem_embedding"
        indexes = [
            HnswIndex(
                name="app_poem_embedding_vector_hnsw",
                fields=["vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Embedding for poem {self.poem_id}"
