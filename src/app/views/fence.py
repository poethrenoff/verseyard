from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models.poem import Poem
from app.utils.fence import find_similar


class PoemSimilarView(APIView):
    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "ready"]},
                    "similar": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "title": {"type": "string"},
                                "comment": {"type": "string"},
                                "similarity": {"type": "number"},
                            },
                        },
                    },
                },
            }
        },
        tags=["Poems"],
    )
    def get(self, request, pk: int):
        poem = get_object_or_404(Poem, pk=pk, author=request.user)

        if not hasattr(poem, "embedding"):
            return Response({"status": "pending", "similar": []})

        return Response({"status": "ready", "similar": find_similar(poem)})
