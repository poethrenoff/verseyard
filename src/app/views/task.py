from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from app.authentication import IsAuthenticated


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "ready", "error"]},
                    "result": {
                        "type": "array",
                        "items": {
                            "type": "object",
                        },
                    },
                    "message": {"type": "string"},
                },
            }
        },
        tags=["Tasks"],
    )
    def get(self, request, task_id: str):
        result = AsyncResult(task_id)

        if not result.ready():
            return Response({"status": "pending"})

        if result.failed():
            return Response({"status": "error", "message": str(result.result)})

        return Response({"status": "ready", "result": result.result})
