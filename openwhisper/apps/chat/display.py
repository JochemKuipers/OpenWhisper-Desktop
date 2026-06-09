"""Computed chat display labels (shared by REST serializers and realtime events)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openwhisper.apps.chat.models import Chat

GROUP_DEFAULT_TITLE = "New group chat"
FALLBACK_TITLE = "Chat"


def ensure_group_default_title(chat: Chat) -> bool:
    """Persist the default group name when a nameless chat reaches 3+ members."""
    if chat.users.count() > 2 and not (chat.title and chat.title.strip()):
        chat.title = GROUP_DEFAULT_TITLE
        chat.save(update_fields=["title", "updated_at"])
        return True
    return False


def revert_group_default_title_if_dm(chat: Chat) -> bool:
    """Drop the auto-generated group title when membership falls back to 1:1."""
    if chat.users.count() <= 2 and chat.title.strip() == GROUP_DEFAULT_TITLE:
        chat.title = ""
        chat.save(update_fields=["title", "updated_at"])
        return True
    return False


def _chat_usernames(chat: Chat) -> list[str]:
    return [u.username for u in chat.users.all() if u.username]


def get_display_title(chat: Chat, user) -> str:
    if chat.title and chat.title.strip():
        return chat.title.strip()
    usernames = _chat_usernames(chat)
    if len(usernames) == 2 and user and getattr(user, "is_authenticated", False):
        other = next((n for n in usernames if n.lower() != user.username.lower()), None)
        if other:
            return other
    if len(usernames) > 2:
        return GROUP_DEFAULT_TITLE
    return FALLBACK_TITLE


def get_member_subtitle(chat: Chat, user) -> str:
    usernames = _chat_usernames(chat)
    if len(usernames) <= 2:
        return ""
    parts = []
    for name in usernames:
        if (
            user
            and getattr(user, "is_authenticated", False)
            and name.lower() == user.username.lower()
        ):
            parts.append("You")
        else:
            parts.append(name)
    return ", ".join(parts)


def build_chat_updated_events(
    chat: Chat, user_ids: list[int] | None = None
) -> list[tuple[int, dict]]:
    """Per-user social events so each client receives its own display_title / member_subtitle."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if user_ids is None:
        user_ids = list(chat.users.values_list("pk", flat=True))
    users_by_id = {u.pk: u for u in User.objects.filter(pk__in=user_ids)}
    events = []
    for uid in user_ids:
        user = users_by_id.get(uid)
        if user is None:
            continue
        events.append(
            (
                uid,
                {
                    "type": "chat_updated",
                    "chat_id": chat.pk,
                    "display_title": get_display_title(chat, user),
                    "member_subtitle": get_member_subtitle(chat, user),
                },
            )
        )
    return events
