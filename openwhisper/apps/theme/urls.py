from django.urls import path
from django.views.generic import RedirectView

from openwhisper.apps.theme.views import (
    AccountSettingsView,
    ChatAppView,
    LandingView,
    ThemeLoginView,
    ThemeLogoutView,
    ThemeRegisterView,
)

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("login/", ThemeLoginView.as_view(), name="login"),
    path("logout/", ThemeLogoutView.as_view(), name="logout"),
    path("register/", ThemeRegisterView.as_view(), name="register"),
    path("account/settings/", AccountSettingsView.as_view(), name="account-settings"),
    path("app/", ChatAppView.as_view(), name="chat-app"),
    path(
        "labs/chat/",
        RedirectView.as_view(pattern_name="chat-app", permanent=False),
        name="chat-lab-redirect",
    ),
]
