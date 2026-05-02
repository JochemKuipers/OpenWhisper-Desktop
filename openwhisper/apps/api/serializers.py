from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from openwhisper.apps.chat.models import Chat, Message
from openwhisper.apps.chat.permissions import chat_admin, is_chat_admin

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "is_staff"]


class PublicUserMiniSerializer(serializers.ModelSerializer):
    """Limited fields for search / friends lists (no email)."""

    class Meta:
        model = User
        fields = ["username"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Current-user profile for GET/PATCH /api/users/me/."""

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "phone_number",
            "gender",
            "birth_date",
            "location",
            "avatar",
        ]
        read_only_fields = ["username"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "phone_number",
            "first_name",
            "last_name",
            "location",
            "gender",
            "birth_date",
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        if validated_data.get("phone_number") == "":
            validated_data["phone_number"] = None
        return User.objects.create_user(password=password, **validated_data)


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    sender = UserSerializer(read_only=True)
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["url", "sender", "content", "attachment_url", "created_at", "updated_at"]

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        url = obj.attachment.url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class ChatSerializer(serializers.HyperlinkedModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=120)
    admin_username = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "url",
            "title",
            "users",
            "messages",
            "created_at",
            "updated_at",
            "admin_username",
            "is_admin",
        ]
        read_only_fields = [
            "url",
            "users",
            "messages",
            "created_at",
            "updated_at",
            "admin_username",
            "is_admin",
        ]

    def get_admin_username(self, obj):
        admin = chat_admin(obj)
        return admin.username if admin else None

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return is_chat_admin(request.user, obj)

    def validate_title(self, value):
        if value is None:
            return ""
        return value.strip()
