from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from app.models.author import Author
from app.models.poem import Poem
from app.models.poem_embedding import PoemEmbedding
from app.tasks import compute_poem_similarity, embed_poem
from app.utils.jwt import jwt_encode


def _fake_encode(texts):
    vectors = []
    for text in texts:
        if "dissimilar" in text:
            vectors.append([1.0, 0.0, 0.0] + [0.0] * 1021)
        else:
            vectors.append([0.0, 1.0, 0.0] + [0.0] * 1021)
    return vectors


@override_settings(FENCE_SIMILARITY_THRESHOLD=0.5, FENCE_SIMILARITY_LIMIT=5)
class FenceTest(TestCase):
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

    def test_embed_poem_creates_embedding(self):
        poem = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        with patch("app.utils.fence.encode", side_effect=_fake_encode):
            embed_poem.run(poem.id)
        embedding = PoemEmbedding.objects.get(poem=poem)
        self.assertEqual(len(embedding.vector), 1024)
        self.assertEqual(embedding.model_name, "BAAI/bge-m3")

    def test_embed_poem_is_idempotent_on_rerun(self):
        poem = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        with patch("app.utils.fence.encode", side_effect=_fake_encode):
            embed_poem.run(poem.id)
            embed_poem.run(poem.id)
        self.assertEqual(PoemEmbedding.objects.filter(poem=poem).count(), 1)

    def test_start_similar_task_returns_task_id(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "fresh poem"}, format="json")
        pk = created.json()["id"]

        response = self.client.post(reverse("poem-similar", args=[pk]))
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertIn("task_id", body)
        self.assertEqual(len(body["task_id"]), 36)

    def test_post_similar_requires_authorship_404_for_other_author(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "mine"}, format="json")
        pk = created.json()["id"]

        self._auth(self.other)
        response = self.client.post(reverse("poem-similar", args=[pk]))
        self.assertEqual(response.status_code, 404)

    def test_task_status_pending_for_unstarted_task(self):
        self._auth(self.author)
        response = self.client.post(reverse("poem-list"), {"content": "fresh poem"}, format="json")
        pk = response.json()["id"]

        start = self.client.post(reverse("poem-similar", args=[pk]))
        task_id = start.json()["task_id"]

        status_response = self.client.get(reverse("task-status", args=[task_id]))
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "pending")

    def test_task_status_ready_returns_stored_result(self):
        self._auth(self.author)
        target = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        similar = Poem.objects.create(author=self.author, title="s", content="similar text", comment="c", active=True)
        with patch("app.utils.fence.encode", side_effect=_fake_encode):
            for poem in (target, similar):
                embed_poem.run(poem.id)

        expected = compute_poem_similarity.run(target.id)

        from celery import current_app

        backend = current_app.backend
        task_id = "11111111-1111-1111-1111-111111111111"
        backend.store_result(task_id, expected, "SUCCESS")

        status_response = self.client.get(reverse("task-status", args=[task_id]))
        data = status_response.json()
        self.assertEqual(data["status"], "ready")
        ids = [item["id"] for item in data["result"]]
        self.assertIn(similar.id, ids)
        self.assertNotIn(target.id, ids)

    def test_task_status_error_returns_message(self):
        self._auth(self.author)

        from celery import current_app

        backend = current_app.backend
        task_id = "22222222-2222-2222-2222-222222222222"
        backend.store_result(task_id, ValueError("embedding failed"), "FAILURE")

        status_response = self.client.get(reverse("task-status", args=[task_id]))
        data = status_response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["message"], "embedding failed")
