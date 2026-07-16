from django.shortcuts import render
from rest_framework.views import APIView


class FrontendView(APIView):
    permission_classes = []

    def get(self, request):
        return render(request, "app/index.html", {})
