"""Chat membership roles (creator is admin)."""


def chat_admin(chat):
    """User who admins the chat: explicit creator, else earliest member by pk (legacy)."""
    if getattr(chat, "created_by_id", None):
        return chat.created_by
    return chat.users.order_by("id").first()


def is_chat_admin(user, chat) -> bool:
    admin = chat_admin(chat)
    return admin is not None and admin.pk == user.pk
