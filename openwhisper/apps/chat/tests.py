import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from openwhisper.apps.chat.models import Chat, Message


@pytest.mark.django_db(transaction=True)
def test_chat_websocket_receives_message_created_broadcast():
    """Connects as a chat member and expects a JSON event when a Message is saved."""
    from openwhisper.asgi import application

    User = get_user_model()
    user = User.objects.create_user(
        username="ws_tester",
        email="ws_tester@example.com",
        password="unused-for-ws-test",
    )
    chat = Chat.objects.create()
    chat.users.add(user)
    token = str(RefreshToken.for_user(user).access_token)

    @database_sync_to_async
    def create_message():
        Message.objects.create(chat=chat, sender=user, content="hello realtime")

    async def ws_flow():
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chats/{chat.pk}/?token={token}",
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await create_message()

        payload = await communicator.receive_json_from(timeout=5)
        assert payload["type"] == "message.created"
        assert payload["content"] == "hello realtime"
        assert payload["sender_id"] == user.pk
        assert payload["sender_username"] == user.username
        assert payload["chat_id"] == chat.pk

        await communicator.disconnect()

    async_to_sync(ws_flow)()
