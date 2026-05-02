import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from openwhisper.apps.chat.models import Chat, Message
from openwhisper.apps.user.models import FriendRequest


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


@pytest.mark.django_db(transaction=True)
def test_social_websocket_friend_send_and_accept_via_ws():
    """Friend request send + accept mutate DB and notify both users over /ws/social/."""
    from openwhisper.asgi import application

    User = get_user_model()
    alice = User.objects.create_user(
        username="soc_alice",
        email="soc_alice@example.com",
        password="pw",
    )
    bob = User.objects.create_user(
        username="soc_bob",
        email="soc_bob@example.com",
        password="pw",
    )
    tok_a = str(RefreshToken.for_user(alice).access_token)
    tok_b = str(RefreshToken.for_user(bob).access_token)

    async def ws_flow():
        comm_bob = WebsocketCommunicator(application, f"/ws/social/?token={tok_b}")
        assert (await comm_bob.connect())[0] is True

        comm_alice = WebsocketCommunicator(application, f"/ws/social/?token={tok_a}")
        assert (await comm_alice.connect())[0] is True

        await comm_alice.send_json_to(
            {"action": "friend_request_send", "op_id": 1, "username": bob.username}
        )

        bob_recv = await comm_bob.receive_json_from(timeout=5)
        assert bob_recv["type"] == "friend_request_received"
        assert bob_recv["username"] == alice.username

        alice_recv = await comm_alice.receive_json_from(timeout=5)
        assert alice_recv["type"] == "friend_request_sent"
        assert alice_recv["username"] == bob.username

        ack = await comm_alice.receive_json_from(timeout=5)
        assert ack["type"] == "social_ack" and ack["ok"] is True

        await comm_bob.send_json_to(
            {"action": "friend_request_accept", "op_id": 2, "username": alice.username}
        )

        got_b = await comm_bob.receive_json_from(timeout=5)
        got_a = await comm_alice.receive_json_from(timeout=5)
        assert got_b["type"] == "friend_request_accepted"
        assert got_b["username"] == alice.username
        assert got_a["type"] == "friend_request_accepted"
        assert got_a["username"] == bob.username

        ack_b = await comm_bob.receive_json_from(timeout=5)
        assert ack_b["type"] == "social_ack" and ack_b["ok"] is True

        await comm_alice.disconnect()
        await comm_bob.disconnect()

    @database_sync_to_async
    def assert_friends():
        assert alice.friends.filter(pk=bob.pk).exists()
        assert bob.friends.filter(pk=alice.pk).exists()
        assert not FriendRequest.objects.filter(from_user=alice, to_user=bob).exists()

    async_to_sync(ws_flow)()
    async_to_sync(assert_friends)()
