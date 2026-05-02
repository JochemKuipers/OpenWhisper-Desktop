import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from openwhisper.apps.chat.friend_social import (
    friend_remove,
    friend_request_accept,
    friend_request_cancel,
    friend_request_send,
)
from openwhisper.apps.chat.models import Chat


class SocialConsumer(AsyncWebsocketConsumer):
    """Per-user social channel: friend requests + unfriend (?token= JWT)."""

    async def connect(self):
        user = self.scope["user"]
        if isinstance(user, AnonymousUser):
            await self.close()
            return
        self.user_group = f"user_{user.pk}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if getattr(self, "user_group", None):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = (data.get("action") or "").strip()
        op_id = data.get("op_id")
        username = data.get("username")
        user = self.scope["user"]

        async def ack_error(detail: str) -> None:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "social_ack",
                        "ok": False,
                        "op_id": op_id,
                        "detail": detail,
                    }
                )
            )

        runner = None
        if action == "friend_request_send":
            runner = friend_request_send
        elif action == "friend_request_accept":
            runner = friend_request_accept
        elif action == "friend_request_cancel":
            runner = friend_request_cancel
        elif action == "friend_remove":
            runner = friend_remove

        if runner is None:
            if op_id is not None:
                await ack_error("Unknown action.")
            return

        if op_id is None:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "social_ack",
                        "ok": False,
                        "op_id": None,
                        "detail": "op_id is required.",
                    }
                )
            )
            return

        ok, err, events = await database_sync_to_async(runner)(user, username)

        if not ok:
            await ack_error(err or "Request failed.")
            return

        for uid, payload in events:
            await self.channel_layer.group_send(
                f"user_{uid}",
                {"type": "social.notify", "payload": payload},
            )
        await self.send(
            text_data=json.dumps(
                {"type": "social_ack", "ok": True, "op_id": op_id, "action": action}
            )
        )

    async def social_notify(self, event):
        await self.send(text_data=json.dumps(event["payload"]))


class ChatConsumer(AsyncWebsocketConsumer):
    """Subscribe to chat_<id> group; receive events of type chat_message."""

    async def connect(self):
        if isinstance(self.scope["user"], AnonymousUser):
            await self.close()
            return

        self.chat_id = int(self.scope["url_route"]["kwargs"]["chat_id"])
        user = self.scope["user"]

        if not await self._user_in_chat(user.pk, self.chat_id):
            await self.close()
            return

        self.group_name = f"chat_{self.chat_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Realtime delivery is driven from the REST layer via group_send; optional client pings.
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    @database_sync_to_async
    def _user_in_chat(self, user_id: int, chat_id: int) -> bool:
        return Chat.objects.filter(pk=chat_id, users__id=user_id).exists()
