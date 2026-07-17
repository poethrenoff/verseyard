from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.test import TestCase
from openai import RateLimitError

from app.models.assessment import PoemAssessment
from app.models.author import Author
from app.models.poem import Poem


def _fake_assess(content):
    return {
        "freshness": 8,
        "emotional_density": 7,
        "voice": 6,
        "completeness": 9,
        "comment": "Крепкий стих.",
    }


def _rate_limit_error(retry_after="2"):
    response = MagicMock()
    response.headers = {"retry-after": retry_after}
    return RateLimitError("rate limited", response=response, body=None)


class BackfillAssessmentsTest(TestCase):
    def setUp(self):
        self.author = Author.objects.create(
            name="Author A",
            email="a@example.com",
            password=make_password("secret123"),
        )
        for i in range(3):
            Poem.objects.create(author=self.author, title=f"t{i}", content=f"poem {i}", comment="", active=True)

    def test_backfill_all_poems(self):
        with (
            patch("app.management.commands.backfill_assessments.assess", side_effect=_fake_assess),
            patch("app.management.commands.backfill_assessments.anti_repeat_score", return_value=10),
            patch("app.utils.llm.assess", side_effect=_fake_assess),
            patch("app.utils.assessment.anti_repeat_score", return_value=10),
        ):
            call_command("backfill_assessments", "--rate-limit", "0", "--batch", "5")

        self.assertEqual(PoemAssessment.objects.count(), 3)
        assessment = PoemAssessment.objects.first()
        self.assertEqual(assessment.freshness, 8)
        self.assertEqual(assessment.anti_repeat, 10)

    def test_backfill_only_missing(self):
        poem = Poem.objects.first()
        PoemAssessment.objects.create(
            poem=poem, freshness=1, emotional_density=1, voice=1, completeness=1, anti_repeat=1
        )
        with (
            patch("app.management.commands.backfill_assessments.assess", side_effect=_fake_assess),
            patch("app.management.commands.backfill_assessments.anti_repeat_score", return_value=10),
            patch("app.utils.llm.assess", side_effect=_fake_assess),
            patch("app.utils.assessment.anti_repeat_score", return_value=10),
        ):
            call_command("backfill_assessments", "--only-missing", "--rate-limit", "0", "--batch", "5")

        self.assertEqual(PoemAssessment.objects.count(), 3)

    def test_backfill_handles_429_with_retry(self):
        calls = {"n": 0}

        def side_effect(content):
            calls["n"] += 1
            if calls["n"] == 1:
                raise _rate_limit_error("1")
            return _fake_assess(content)

        with (
            patch("app.management.commands.backfill_assessments.assess", side_effect=side_effect),
            patch("app.management.commands.backfill_assessments.anti_repeat_score", return_value=10),
            patch("time.sleep"),
            patch("app.utils.llm.assess", side_effect=side_effect),
            patch("app.utils.assessment.anti_repeat_score", return_value=10),
        ):
            call_command("backfill_assessments", "--rate-limit", "0", "--batch", "5", "--max-retries", "3")

        self.assertEqual(PoemAssessment.objects.count(), 3)
        self.assertEqual(calls["n"], 4)

    def test_backfill_gives_up_after_max_retries(self):
        with (
            patch(
                "app.management.commands.backfill_assessments.assess",
                side_effect=_rate_limit_error("0"),
            ),
            patch("app.management.commands.backfill_assessments.anti_repeat_score", return_value=10),
            patch("time.sleep"),
            patch("app.utils.llm.assess", side_effect=_rate_limit_error("0")),
            patch("app.utils.assessment.anti_repeat_score", return_value=10),
        ):
            call_command("backfill_assessments", "--rate-limit", "0", "--batch", "5", "--max-retries", "2")

        self.assertEqual(PoemAssessment.objects.count(), 0)
