from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openwhisper.apps.chat"
    label = "chat"

    def ready(self):
        import openwhisper.apps.chat.signals  # noqa: F401
