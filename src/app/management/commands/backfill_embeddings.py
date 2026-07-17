from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from app.models.poem import Poem
from app.models.poem_embedding import PoemEmbedding


class Command(BaseCommand):
    help = "Вычисляет эмбеддинги для стихов без вектора (или с другой моделью)"

    def add_arguments(self, parser):
        parser.add_argument("--author", type=int, default=None, help="ID автора (по умолчанию все)")
        parser.add_argument("--batch", type=int, default=32, help="Размер батча")

    def handle(self, *args, **options):
        from app.utils.similar import encode

        author_id = options["author"]
        batch_size = options["batch"]

        poems = (
            Poem.objects.filter(active=True)
            .select_related("author")
            .prefetch_related(Prefetch("embedding", queryset=PoemEmbedding.objects.only("poem_id", "model_name")))
        )
        if author_id is not None:
            poems = poems.filter(author_id=author_id)

        total = poems.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Нет стихов для обработки."))
            return

        processed = 0
        pending = [
            p for p in poems if not hasattr(p, "embedding") or p.embedding.model_name != settings.EMBEDDING_MODEL_NAME
        ]

        self.stdout.write(f"Всего стихов: {total}, требуют эмбеддинга: {len(pending)}")

        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            texts = [poem.content for poem in batch]
            vectors = encode(texts)

            for poem, vector in zip(batch, vectors, strict=True):
                PoemEmbedding.objects.update_or_create(
                    poem=poem,
                    defaults={"vector": vector, "model_name": settings.EMBEDDING_MODEL_NAME},
                )
            processed += len(batch)
            self.stdout.write(f"Обработано {processed}/{len(pending)}")

        self.stdout.write(self.style.SUCCESS("Бэкфилл эмбеддингов завершён."))
