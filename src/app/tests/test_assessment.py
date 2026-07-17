from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from app.models.assessment import PoemAssessment
from app.models.author import Author
from app.models.poem import Poem
from app.tasks import assess_poem, embed_poem
from app.utils.jwt import jwt_encode


def _fake_assess(content):
    return {
        "freshness": 8,
        "emotional_density": 7,
        "voice": 6,
        "completeness": 9,
        "comment": "Крепкий стих.",
    }


def _fake_encode(texts):
    vectors = []
    for text in texts:
        if "dissimilar" in text:
            vectors.append([1.0, 0.0, 0.0] + [0.0] * 1021)
        else:
            vectors.append([0.0, 1.0, 0.0] + [0.0] * 1021)
    return vectors


class AssessmentTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "secret123"
        self.author = Author.objects.create(
            name="Author A",
            email="a@example.com",
            password=make_password(self.password),
        )
        self.other = Author.objects.create(
            name="Author B",
            email="b@example.com",
            password=make_password(self.password),
        )

    def _auth(self, author):
        token = jwt_encode({"id": author.id, "name": author.name, "email": author.email})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_assess_poem_creates_assessment(self):
        poem = Poem.objects.create(author=self.author, title="t", content="fresh poem", comment="", active=True)
        with (
            patch("app.utils.llm.assess", side_effect=_fake_assess),
            patch("app.utils.assessment.anti_repeat_score", return_value=10),
        ):
            assess_poem.run(poem.id)

        assessment = PoemAssessment.objects.get(poem=poem)
        self.assertEqual(assessment.freshness, 8)
        self.assertEqual(assessment.emotional_density, 7)
        self.assertEqual(assessment.voice, 6)
        self.assertEqual(assessment.completeness, 9)
        self.assertEqual(assessment.anti_repeat, 10)
        self.assertEqual(assessment.comment, "Крепкий стих.")

    def test_assess_poem_is_idempotent_on_rerun(self):
        poem = Poem.objects.create(author=self.author, title="t", content="fresh poem", comment="", active=True)
        with (
            patch("app.utils.llm.assess", side_effect=_fake_assess),
            patch("app.utils.assessment.anti_repeat_score", return_value=None),
        ):
            assess_poem.run(poem.id)
            assess_poem.run(poem.id)
        self.assertEqual(PoemAssessment.objects.filter(poem=poem).count(), 1)

    def test_assessment_endpoint_returns_task_id(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "fresh poem"}, format="json")
        pk = created.json()["id"]

        response = self.client.post(reverse("poem-assessment", args=[pk]))
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertIn("task_id", body)
        self.assertEqual(len(body["task_id"]), 36)

    def test_assessment_endpoint_requires_authorship_404_for_other_author(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "mine"}, format="json")
        pk = created.json()["id"]

        self._auth(self.other)
        response = self.client.post(reverse("poem-assessment", args=[pk]))
        self.assertEqual(response.status_code, 404)

    def test_task_status_ready_returns_stored_result(self):
        self._auth(self.author)
        poem = Poem.objects.create(author=self.author, title="t", content="fresh poem", comment="", active=True)
        with (
            patch("app.utils.llm.assess", side_effect=_fake_assess),
            patch("app.utils.assessment.anti_repeat_score", return_value=4),
        ):
            result = assess_poem.run(poem.id)

        from celery import current_app

        backend = current_app.backend
        task_id = "22222222-2222-2222-2222-222222222222"
        backend.store_result(task_id, result, "SUCCESS")

        status_response = self.client.get(reverse("task-status", args=[task_id]))
        data = status_response.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["result"]["scores"]["freshness"], 8)
        self.assertEqual(data["result"]["scores"]["anti_repeat"], 4)
        self.assertEqual(data["result"]["comment"], "Крепкий стих.")
        self.assertEqual(data["result"]["model_name"], settings.LLM_MODEL_NAME)

    def test_anti_repeat_none_without_embedding(self):
        from app.utils.assessment import anti_repeat_score

        poem = Poem.objects.create(author=self.author, title="t", content="fresh poem", comment="", active=True)
        self.assertIsNone(anti_repeat_score(poem))

    def test_anti_repeat_scores_from_embedding(self):
        from app.utils.assessment import anti_repeat_score

        target = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        similar = Poem.objects.create(author=self.author, title="s", content="similar text", comment="c", active=True)
        with patch("app.utils.similar.encode", side_effect=_fake_encode):
            for poem in (target, similar):
                embed_poem.run(poem.id)

        # "similar text" are near-identical -> low anti_repeat score
        self.assertLessEqual(anti_repeat_score(target), 2)

        dissimilar = Poem.objects.create(
            author=self.author, title="d", content="dissimilar text", comment="c", active=True
        )
        with patch("app.utils.similar.encode", side_effect=_fake_encode):
            embed_poem.run(dissimilar.id)

        # dissimilar has no close neighbors -> high anti_repeat score
        self.assertGreaterEqual(anti_repeat_score(dissimilar), 9)

    def test_stats_returns_average_scores(self):
        self._auth(self.author)
        for i in range(2):
            poem = Poem.objects.create(author=self.author, title="t", content=f"poem {i}", comment="", active=True)
            PoemAssessment.objects.create(
                poem=poem,
                freshness=6 + i,
                emotional_density=7,
                voice=5,
                completeness=8,
                anti_repeat=10,
            )

        response = self.client.get(reverse("poem-stats"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count_assessed"], 2)
        self.assertAlmostEqual(data["avg_scores"]["freshness"], 6.5)
        self.assertEqual(data["avg_scores"]["anti_repeat"], 10)
