from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from openwhisper.apps.api.serializers import ChatSerializer, MessageSerializer, UserSerializer
from openwhisper.apps.chat.models import Chat, Message
from django.http import Http404

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]
    
    queryset = User.objects.all()
    serializer_class = UserSerializer

class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]

    queryset = Message.objects.select_related("sender", "chat").order_by("-created_at")
    serializer_class = MessageSerializer


class ChatViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated | permissions.IsAdminUser]

    queryset = Chat.objects.prefetch_related(
        "users",
        Prefetch(
            "messages",
            queryset=Message.objects.select_related("sender").order_by("created_at"),
        ),
    )
    serializer_class = ChatSerializer
    

class UserChatsAPIView(APIView):
    """
    Get all chats for a user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Http404
    
    def get(self, request, user_id):
        user = self.get_object(user_id)
        chats = Chat.objects.filter(users=user)
        serializer = ChatSerializer(chats, many=True)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request, user_id):
        user = self.get_object(user_id)
        chat = Chat.objects.create(users=[user])
        serializer = ChatSerializer(chat)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            chat = Chat.objects.filter(users=user).first()
            chat.delete()
            return Response("Chat deleted successfully", status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response("Chat not found", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
class ChatMessagesAPIView(APIView):
    """
    Get all messages for a chat
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return Http404
        
    def get(self, request, chat_id):
        chat = self.get_object(chat_id)
        messages = chat.messages.all()
        serializer = MessageSerializer(messages, many=True)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request, chat_id):
        chat = self.get_object(chat_id)
        message = Message.objects.create(chat=chat, sender=request.user, content=request.data.get('content'))
        serializer = MessageSerializer(message)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, chat_id):
        try:
            chat = self.get_object(chat_id)
            chat.delete()
            return Response("Chat deleted successfully", status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response("Chat not found", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)