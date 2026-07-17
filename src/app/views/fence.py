from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models.poem import Poem
from app.tasks import compute_poem_similarity


class PoemSimilarView(APIView):
    @extend_schema(
        responses=OpenApiResponse(
            description="Task queued. Poll GET /api/tasks/{task_id}/ for the result.",
            response={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
            },
        ),
        tags=["Poems"],
    )
    def post(self, request, pk: int):
        poem = get_object_or_404(Poem, pk=pk, author=request.user)
        task = compute_poem_similarity.apply_async(args=[poem.id])
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
