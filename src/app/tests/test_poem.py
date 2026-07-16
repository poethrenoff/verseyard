from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from app.models.author import Author
from app.models.collection import Collection
from app.models.poem import Poem
from app.utils.poem import derive_comment, derive_title, normalize_content


class PoemUtilsTest(TestCase):
    def test_normalize_content_strips_trailing_and_blank_edges(self):
        content = "\n  line one  \n  line two\n\n  line three  \n\n"
        result = normalize_content(content)
        self.assertEqual(result, "  line one\n  line two\n\n  line three")

    def test_normalize_content_keeps_inner_blank_lines(self):
        content = "one\n\n\ntwo"
        self.assertEqual(normalize_content(content), "one\n\n\ntwo")

    def test_derive_title_explicit(self):
        self.assertEqual(derive_title("any", "My Title"), "My Title")

    def test_derive_title_from_first_line(self):
        content = "Петрович переживает.  \nвторой стих."
        self.assertEqual(derive_title(content, ""), '"Петрович переживает..."')

    def test_derive_title_strips_punctuation(self):
        content = "Тире — конец!\n"
        self.assertEqual(derive_title(content, ""), '"Тире — конец..."')

    def test_derive_title_empty_content(self):
        self.assertEqual(derive_title("\n\n", ""), "")

    def test_derive_comment_explicit(self):
        self.assertEqual(derive_comment("notes"), "notes")

    def test_derive_comment_today(self):
        expected = timezone.localdate().strftime("%d.%m.%Y")
        self.assertEqual(derive_comment(""), expected)


class PoemAPITest(TestCase):
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
        self.collection = Collection.objects.create(author=self.author, title="C", comment="")

    def _token(self, author):
        from app.utils.jwt import jwt_encode

        return jwt_encode({"id": author.id, "name": author.name, "email": author.email})

    def _auth(self, author):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._token(author)}")

    def test_create_derives_title_and_comment(self):
        self._auth(self.author)
        response = self.client.post(
            reverse("poem-list"),
            {"content": "Петрович переживает.  \nвторой стих."},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], '"Петрович переживает..."')
        self.assertEqual(data["comment"], timezone.localdate().strftime("%d.%m.%Y"))
        poem = Poem.objects.get(id=data["id"])
        self.assertEqual(poem.content, "Петрович переживает.\nвторой стих.")

    def test_create_normalizes_content(self):
        self._auth(self.author)
        response = self.client.post(reverse("poem-list"), {"content": "  text  \n\n  more  \n"}, format="json")
        self.assertEqual(response.json()["content"], "  text\n\n  more")

    def test_list_query_search(self):
        self._auth(self.author)
        self.client.post(reverse("poem-list"), {"content": "uniquekeyword here"}, format="json")
        self.client.post(reverse("poem-list"), {"content": "nothing"}, format="json")
        response = self.client.get(reverse("poem-list") + "?query=uniquekeyword")
        results = response.json()["results"]
        self.assertEqual(len(results), 1)

    def test_patch_updates_and_normalizes_content(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "orig", "title": "Keep"}, format="json")
        pk = created.json()["id"]
        response = self.client.patch(
            reverse("poem-update", args=[pk]), {"content": "  new content here.  "}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "  new content here.")
        self.assertEqual(data["title"], '"new content here..."')

    def test_patch_derives_title_and_comment_when_omitted(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "Стих для пересчёта."}, format="json")
        pk = created.json()["id"]
        response = self.client.patch(
            reverse("poem-update", args=[pk]), {"content": "Другой текст стиха.  "}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "Другой текст стиха.")
        self.assertEqual(data["title"], '"Другой текст стиха..."')
        self.assertEqual(data["comment"], timezone.localdate().strftime("%d.%m.%Y"))

    def test_patch_keeps_explicit_title_and_comment(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "исходный"}, format="json")
        pk = created.json()["id"]
        response = self.client.patch(
            reverse("poem-update", args=[pk]),
            {"content": "изменённый текст.", "title": "Свой заголовок", "comment": "Свой коммент"},
            format="json",
        )
        data = response.json()
        self.assertEqual(data["title"], "Свой заголовок")
        self.assertEqual(data["comment"], "Свой коммент")

    def test_patch_isolation_404_for_other_author(self):
        self._auth(self.author)
        created = self.client.post(reverse("poem-list"), {"content": "mine"}, format="json")
        pk = created.json()["id"]

        self._auth(self.other)
        response = self.client.patch(reverse("poem-update", args=[pk]), {"content": "hack"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_unauthorized_returns_401(self):
        response = self.client.get(reverse("poem-list"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["type"], "InvalidJWTTokenError")

    def test_stats_counts_collection_and_uncategorized(self):
        self._auth(self.author)
        self.client.post(reverse("poem-list"), {"content": "вне коллекции"}, format="json")
        self.client.post(reverse("poem-list"), {"content": "в коллекции"}, format="json")
        poem = Poem.objects.filter(author=self.author).order_by("id").last()
        poem.collection = self.collection
        poem.save()

        self._auth(self.other)
        self.client.post(reverse("poem-list"), {"content": "чужой"}, format="json")

        self._auth(self.author)
        response = self.client.get(reverse("poem-stats"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["in_collection"], 1)
        self.assertEqual(data["uncategorized"], 1)
        self.assertEqual(data["remaining"], 100000 - 2)

    def test_stats_ignores_inactive_poems(self):
        self._auth(self.author)
        self.client.post(reverse("poem-list"), {"content": "активный"}, format="json")
        inactive = Poem.objects.create(
            author=self.author,
            title="hidden",
            content="скрытый",
            comment="",
            active=False,
        )

        response = self.client.get(reverse("poem-stats"))
        data = response.json()
        self.assertEqual(data["uncategorized"], 1)
        self.assertEqual(data["in_collection"], 0)
        self.assertEqual(data["remaining"], 100000 - 1)
