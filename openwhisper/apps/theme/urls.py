from django.urls import path
from openwhisper.apps.theme.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]