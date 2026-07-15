from django.urls import path

from app.views.auth import InfoView, LoginView, TokenRefreshView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/info/", InfoView.as_view(), name="info"),
]
