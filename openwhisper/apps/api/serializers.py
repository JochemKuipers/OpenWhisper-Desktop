from django.contrib.auth import get_user_model
from rest_framework import serializers

from openwhisper.apps.chat.models import Chat, Message

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "is_staff"]


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["url", "sender", "content", "created_at", "updated_at"]


class ChatSerializer(serializers.HyperlinkedModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Chat
        fields = ["url", "users", "messages", "created_at", "updated_at"]
