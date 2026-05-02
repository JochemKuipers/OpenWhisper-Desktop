from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.db.models import Count, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework_simplejwt.tokens import RefreshToken

from openwhisper.apps.api.serializers import (
    ChatSerializer,
    MessageSerializer,
    PublicUserMiniSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
)
from openwhisper.apps.chat.models import Chat, Message

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]

    queryset = User.objects.all()
    serializer_class = UserSerializer


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SessionTokenAPIView(APIView):
    """Mint JWT pair for an active Django session (same shape as SimpleJWT token endpoint)."""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def post(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class UserSearchAPIView(APIView):
    """Find users by username (substring). Excludes self; does not expose email."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])
        qs = (
            User.objects.filter(username__icontains=q)
            .exclude(pk=request.user.pk)
            .order_by("username")[:25]
        )
        ser = PublicUserMiniSerializer(qs, many=True)
        return Response(ser.data)


class MeFriendsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friends = request.user.friends.all().order_by("username")
        ser = PublicUserMiniSerializer(friends, many=True)
        return Response(ser.data)

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        if not username:
            return Response({"detail": "username is required."}, status=status.HTTP_400_BAD_REQUEST)
        if username.lower() == request.user.username.lower():
            return Response({"detail": "You cannot add yourself."}, status=status.HTTP_400_BAD_REQUEST)
        other = get_object_or_404(User, username__iexact=username)
        request.user.friends.add(other)
        ser = PublicUserMiniSerializer(other)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class MeFriendDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, username):
        other = get_object_or_404(User, username__iexact=username)
        request.user.friends.remove(other)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StartDmChatAPIView(APIView):
    """Get or create a 1:1 chat with a friend."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        if not username:
            return Response({"detail": "username is required."}, status=status.HTTP_400_BAD_REQUEST)
        other = get_object_or_404(User, username__iexact=username)
        if other.pk == request.user.pk:
            return Response({"detail": "Cannot start a chat with yourself."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.friends.filter(pk=other.pk).exists():
            return Response(
                {"detail": "You can only start a chat with someone on your friends list."},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing = (
            Chat.objects.annotate(num_users=Count("users"))
            .filter(num_users=2, users=request.user)
            .filter(users=other)
            .prefetch_related(
                "users",
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender").order_by("created_at"),
                ),
            )
            .first()
        )
        if existing:
            return Response(ChatSerializer(existing, context={"request": request}).data)

        chat = Chat.objects.create()
        chat.users.add(request.user, other)
        chat.refresh_from_db()
        chat = (
            Chat.objects.prefetch_related(
                "users",
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender").order_by("created_at"),
                ),
            )
            .get(pk=chat.pk)
        )
        return Response(ChatSerializer(chat, context={"request": request}).data, status=status.HTTP_201_CREATED)


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]

    queryset = Message.objects.select_related("sender", "chat").order_by("-created_at")
    serializer_class = MessageSerializer


class ChatViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]

    serializer_class = ChatSerializer

    def get_queryset(self):
        qs = Chat.objects.prefetch_related(
            "users",
            Prefetch(
                "messages",
                queryset=Message.objects.select_related("sender").order_by("created_at"),
            ),
        ).order_by("-updated_at")
        return qs.filter(users=self.request.user).distinct()


class ChatMessagesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            raise Http404()

    def get(self, request, chat_id):
        chat = self.get_object(chat_id)
        if not chat.users.filter(pk=request.user.pk).exists():
            return Response({"detail": "You are not a member of this chat."}, status=status.HTTP_403_FORBIDDEN)
        messages = chat.messages.all()
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, chat_id):
        chat = self.get_object(chat_id)
        if not chat.users.filter(pk=request.user.pk).exists():
            return Response(
                {"detail": "You are not a member of this chat."},
                status=status.HTTP_403_FORBIDDEN,
            )
        content = request.data.get("content")
        if content is None or (isinstance(content, str) and not content.strip()):
            return Response(
                {"detail": "Message content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = Message.objects.create(chat=chat, sender=request.user, content=content)
        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, chat_id):
        try:
            chat = self.get_object(chat_id)
            chat.delete()
            return Response("Chat deleted successfully", status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response("Chat not found", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "User registered successfully"}, status=status.HTTP_201_CREATED)
