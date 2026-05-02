from django.urls import path

from openwhisper.apps.theme.views import ChatLabView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("labs/chat/", ChatLabView.as_view(), name="chat-lab"),
]