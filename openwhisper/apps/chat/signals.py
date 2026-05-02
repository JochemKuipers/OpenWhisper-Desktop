from django.db.models.signals import post_save
from django.dispatch import receiver

from openwhisper.apps.chat.models import Message
from openwhisper.apps.chat.realtime import broadcast_chat_message


@receiver(post_save, sender=Message)
def notify_ws_on_message(sender, instance: Message, created: bool, **kwargs):
    if not created:
        return
    broadcast_chat_message(
        chat_id=instance.chat_id,
        payload={
            "type": "message.created",
            "message_id": instance.pk,
            "chat_id": instance.chat_id,
            "sender_id": instance.sender_id,
            "sender_username": instance.sender.username,
            "content": instance.content,
            "created_at": instance.created_at.isoformat(),
        },
    )
