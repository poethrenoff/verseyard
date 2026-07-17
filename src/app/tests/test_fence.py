from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from app.models.author import Author
from app.models.poem import Poem
from app.models.poem_embedding import PoemEmbedding
from app.tasks import embed_poem
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

    def test_similar_endpoint_pending_without_embedding(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "fresh poem"}, format="json")
        pk = created.json()["id"]
        response = self.client.get(reverse("poem-similar", args=[pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "pending", "similar": []})

    def test_similar_endpoint_ready_filters_by_threshold_and_excludes_self(self):
        self._auth(self.author)
        target = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        similar = Poem.objects.create(author=self.author, title="s", content="similar text", comment="c", active=True)
        dissimilar = Poem.objects.create(
            author=self.author, title="d", content="dissimilar text", comment="", active=True
        )
        with patch("app.utils.fence.encode", side_effect=_fake_encode):
            for poem in (target, similar, dissimilar):
                embed_poem.run(poem.id)

        response = self.client.get(reverse("poem-similar", args=[target.id]))
        data = response.json()
        self.assertEqual(data["status"], "ready")
        ids = [item["id"] for item in data["similar"]]
        self.assertIn(similar.id, ids)
        self.assertNotIn(dissimilar.id, ids)
        self.assertNotIn(target.id, ids)
        for item in data["similar"]:
            self.assertGreaterEqual(item["similarity"], 0.5)

    def test_similar_excludes_inactive_and_other_authors(self):
        self._auth(self.author)
        target = Poem.objects.create(author=self.author, title="t", content="similar text", comment="", active=True)
        inactive = Poem.objects.create(author=self.author, title="i", content="similar text", comment="", active=False)
        other_poem = Poem.objects.create(author=self.other, title="o", content="similar text", comment="", active=True)
        with patch("app.utils.fence.encode", side_effect=_fake_encode):
            for poem in (target, inactive, other_poem):
                embed_poem.run(poem.id)

        response = self.client.get(reverse("poem-similar", args=[target.id]))
        ids = [item["id"] for item in response.json()["similar"]]
        self.assertNotIn(inactive.id, ids)
        self.assertNotIn(other_poem.id, ids)

    def test_similar_isolation_404_for_other_author(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "mine"}, format="json")
        pk = created.json()["id"]

        self._auth(self.other)
        response = self.client.get(reverse("poem-similar", args=[pk]))
        self.assertEqual(response.status_code, 404)
