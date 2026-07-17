import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import RateLimitError

from app.models.assessment import PoemAssessment
from app.models.poem import Poem
from app.utils.assessment import anti_repeat_score
from app.utils.llm import assess


class Command(BaseCommand):
    help = "Проставляет оценки всем активным стихам (через LLM) с учётом лимитов и 429"

    def add_arguments(self, parser):
        parser.add_argument("--author", type=int, default=None, help="ID автора (по умолчанию все)")
        parser.add_argument("--batch", type=int, default=10, help="Размер пачки за один проход")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            default=False,
            help="Оценивать только стихи без оценки (по умолчанию все активные)",
        )
        parser.add_argument(
            "--rate-limit",
            type=float,
            default=1.0,
            help="Минимальная пауза между запросами к LLM, сек (защита от 429)",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=5,
            help="Максимум повторов при 429 на один стих",
        )

    def handle(self, *args, **options):
        if not settings.LLM_API_URL or not settings.LLM_MODEL_NAME:
            raise CommandError("LLM not configured: set LLM_API_URL and LLM_MODEL_NAME")

        author_id = options["author"]
        batch_size = options["batch"]
        only_missing = options["only_missing"]
        rate_limit = options["rate_limit"]
        max_retries = options["max_retries"]

        poems = Poem.objects.filter(active=True).select_related("author")
        if author_id is not None:
            poems = poems.filter(author_id=author_id)
        if only_missing:
            poems = poems.exclude(assessment__isnull=False)

        total = poems.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Нет стихов для оценки."))
            return

        self.stdout.write(f"Всего стихов к оценке: {total}")

        processed = 0
        failed = 0
        last_call = 0.0

        for poem in poems.iterator(chunk_size=batch_size):
            scores = self._assess_with_retries(poem, rate_limit, max_retries, last_call)
            last_call = time.monotonic()

            if scores is None:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  Пропущен стих {poem.id} (не удалось оценить)"))
                processed += 1
                continue

            scores["anti_repeat"] = anti_repeat_score(poem)
            scores["model_name"] = settings.LLM_MODEL_NAME or ""

            PoemAssessment.objects.update_or_create(poem=poem, defaults=scores)
            processed += 1
            self.stdout.write(f"Оценён стих {poem.id} ({processed}/{total})")

        if failed:
            self.stdout.write(self.style.WARNING(f"Завершено: {processed - failed} ок, {failed} с ошибкой."))
        else:
            self.stdout.write(self.style.SUCCESS("Бэкфилл оценок завершён."))

    def _assess_with_retries(self, poem, rate_limit, max_retries, last_call):
        attempts = 0
        while True:
            sleep_for = rate_limit - (time.monotonic() - last_call)
            if sleep_for > 0:
                time.sleep(sleep_for)
            try:
                return assess(poem.content)
            except RateLimitError as error:
                attempts += 1
                if attempts > max_retries:
                    self.stderr.write(self.style.ERROR(f"  429 на стихе {poem.id}: исчерпаны повторы"))
                    return None
                retry_after = self._retry_after(error)
                self.stdout.write(
                    self.style.WARNING(
                        f"  429 на стихе {poem.id}: пауза {retry_after:.1f}с (попытка {attempts}/{max_retries})"
                    )
                )
                time.sleep(retry_after)
            except Exception as error:
                self.stderr.write(self.style.ERROR(f"  Ошибка оценки стиха {poem.id}: {error}"))
                return None

    @staticmethod
    def _retry_after(error: RateLimitError) -> float:
        headers = getattr(getattr(error, "response", None), "headers", None) or {}
        if value := headers.get("retry-after"):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        return 30.0
