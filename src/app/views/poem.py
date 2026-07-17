from django.conf import settings
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from app.exceptions import InvalidFormError
from app.models.poem import Poem
from app.serializers import (
    PoemCreateSerializer,
    PoemListQuerySerializer,
    PoemSerializer,
    PoemUpdateSerializer,
)
from app.tasks import embed_poem
from app.utils.poem import derive_comment, derive_title, normalize_content


class PoemBaseView(APIView):
    pagination_class = PageNumberPagination


class PoemListCreateView(PoemBaseView):
    @extend_schema(
        methods=["POST"],
        request=PoemCreateSerializer,
        responses=PoemSerializer,
        tags=["Poems"],
    )
    def post(self, request):
        serializer = PoemCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise InvalidFormError(serializer)

        validated = serializer.validated_data
        content = normalize_content(validated["content"])
        title = derive_title(content, validated.get("title"))
        comment = derive_comment(validated.get("comment"))

        position = (
            Poem.objects.filter(author=request.user, collection__isnull=True).aggregate(max_position=Max("position"))[
                "max_position"
            ]
            or 0
        ) + 1

        poem = Poem.objects.create(
            author=request.user,
            collection=None,
            title=title,
            content=content,
            comment=comment,
            position=position,
            active=True,
        )

        embed_poem.apply_async(args=[poem.id], queue=settings.EMBEDDING_QUEUE)

        return Response(PoemSerializer(poem).data, status=201)

    @extend_schema(
        methods=["GET"],
        responses=PoemSerializer(many=True),
        tags=["Poems"],
    )
    def get(self, request):
        query_serializer = PoemListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            raise InvalidFormError(query_serializer)

        validated = query_serializer.validated_data
        collection = validated["collection"]

        poems = Poem.objects.filter(author=request.user, collection=collection)

        query = validated["query"]
        if query:
            poems = poems.filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(comment__icontains=query))

        poems = poems.order_by("position")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(poems, request, view=self)
        serializer = PoemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PoemStatsView(PoemBaseView):
    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "in_collection": {"type": "integer"},
                    "uncategorized": {"type": "integer"},
                    "remaining": {"type": "integer"},
                },
            }
        },
        tags=["Poems"],
    )
    def get(self, request):
        active_poems = Poem.objects.filter(author=request.user, active=True)
        in_collection = active_poems.filter(collection__isnull=False).count()
        uncategorized = active_poems.filter(collection__isnull=True).count()
        total = in_collection + uncategorized
        return Response(
            {
                "in_collection": in_collection,
                "uncategorized": uncategorized,
                "remaining": max(0, 100000 - total),
            }
        )


class PoemDetailView(PoemBaseView):
    @extend_schema(
        methods=["PUT"],
        request=PoemUpdateSerializer,
        responses=PoemSerializer,
        tags=["Poems"],
    )
    def put(self, request, pk: int):
        poem = get_object_or_404(Poem, pk=pk, author=request.user)

        serializer = PoemUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            raise InvalidFormError(serializer)

        validated = serializer.validated_data
        poem.content = normalize_content(validated["content"])
        poem.title = derive_title(poem.content, validated.get("title"))
        poem.comment = derive_comment(validated.get("comment"))

        poem.save()

        embed_poem.apply_async(args=[poem.id], queue=settings.EMBEDDING_QUEUE)

        return Response(PoemSerializer(poem).data, status=200)
