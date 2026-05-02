from django.conf import settings
from django.db import models


class Chat(models.Model):
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
    )
    title = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat between {self.users.all()}"
    
    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        db_table = "chats"
        app_label = "chat"

class Message(models.Model):
    chat = models.ForeignKey(
        "chat.Chat",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.chat.users.all()}"
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["chat", "created_at"]),
        ]
        db_table = "messages"
        app_label = "chat"