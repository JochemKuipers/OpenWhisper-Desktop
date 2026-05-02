import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from openwhisper.apps.chat.models import Chat


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
