from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from openwhisper.apps.api.views import (
    ChatInviteAPIView,
    ChatMessagesAPIView,
    ChatRemoveMemberAPIView,
    ChatViewSet,
    CurrentUserAPIView,
    FriendRequestAcceptAPIView,
    FriendRequestCancelAPIView,
    FriendRequestsAPIView,
    LogoutAPIView,
    MeFriendDetailAPIView,
    MeFriendsAPIView,
    MessageViewSet,
    RegisterAPIView,
    SessionTokenAPIView,
    StartDmChatAPIView,
    UserSearchAPIView,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"chats", ChatViewSet, basename="chat")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("auth/session-token/", SessionTokenAPIView.as_view(), name="api-session-token"),
    path("users/search/", UserSearchAPIView.as_view(), name="user-search"),
    path(
        "users/me/friend-requests/<str:username>/accept/",
        FriendRequestAcceptAPIView.as_view(),
        name="friend-request-accept",
    ),
    path(
        "users/me/friend-requests/<str:username>/",
        FriendRequestCancelAPIView.as_view(),
        name="friend-request-cancel",
    ),
    path("users/me/friend-requests/", FriendRequestsAPIView.as_view(), name="friend-requests"),
    path("users/me/friends/<str:username>/", MeFriendDetailAPIView.as_view(), name="me-friend-detail"),
    path("users/me/friends/", MeFriendsAPIView.as_view(), name="me-friends"),
    path("users/me/", CurrentUserAPIView.as_view(), name="current-user"),
    path("chats/start/", StartDmChatAPIView.as_view(), name="chat-start-dm"),
    path("chats/<int:chat_id>/invite/", ChatInviteAPIView.as_view(), name="chat-invite"),
    path(
        "chats/<int:chat_id>/members/<str:username>/",
        ChatRemoveMemberAPIView.as_view(),
        name="chat-remove-member",
    ),
    path("chats/<int:chat_id>/messages/", ChatMessagesAPIView.as_view(), name="chat-messages"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("", include(router.urls)),
]
