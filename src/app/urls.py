from django.urls import path

from app.views.auth import InfoView, LoginView, TokenRefreshView
from app.views.fence import PoemSimilarView
from app.views.poem import PoemDetailView, PoemListCreateView, PoemStatsView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/info/", InfoView.as_view(), name="info"),
    path("poems/", PoemListCreateView.as_view(), name="poem-list"),
    path("poems/stats/", PoemStatsView.as_view(), name="poem-stats"),
    path("poems/<int:pk>/", PoemDetailView.as_view(), name="poem-update"),
    path("poems/<int:pk>/similar/", PoemSimilarView.as_view(), name="poem-similar"),
]
