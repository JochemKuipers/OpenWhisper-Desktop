"""Notify WebSocket subscribers when a chat event occurs (call from REST or tasks)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def dispatch_social_events(events: list[tuple[int, dict]]) -> None:
    """Push friend-request notifications to per-user channel groups."""
    layer = get_channel_layer()
    if layer is None or not events:
        return
    for user_id, payload in events:
        async_to_sync(layer.group_send)(
            f"user_{user_id}",
            {"type": "social.notify", "payload": payload},
        )


def broadcast_chat_message(*, chat_id: int, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f"chat_{chat_id}",
        {"type": "chat.message", "payload": payload},
    )
