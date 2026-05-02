"""Friend request mutations + WebSocket fan-out targets (shared by REST and SocialConsumer)."""

from __future__ import annotations

from typing import List, Optional, Tuple

from django.contrib.auth import get_user_model

from openwhisper.apps.user.models import FriendRequest

User = get_user_model()

# (user_id, payload) for channel layer group_send
SocialEvent = Tuple[int, dict]


def friend_request_send(actor: User, username: str) -> Tuple[bool, Optional[str], List[SocialEvent]]:
    username = (username or "").strip()
    if not username:
        return False, "username is required.", []
    if username.lower() == actor.username.lower():
        return False, "You cannot add yourself.", []
    other = User.objects.filter(username__iexact=username).first()
    if other is None:
        return False, "User not found.", []
    if actor.friends.filter(pk=other.pk).exists():
        return False, "You are already friends.", []
    if FriendRequest.objects.filter(from_user=actor, to_user=other).exists():
        return False, "Friend request already sent.", []
    if FriendRequest.objects.filter(from_user=other, to_user=actor).exists():
        return (
            False,
            "This user already sent you a friend request. Accept it under Friend requests.",
            [],
        )
    FriendRequest.objects.create(from_user=actor, to_user=other)
    events: List[SocialEvent] = [
        (other.pk, {"type": "friend_request_received", "username": actor.username}),
        (actor.pk, {"type": "friend_request_sent", "username": other.username}),
    ]
    return True, None, events


def friend_request_accept(actor: User, username: str) -> Tuple[bool, Optional[str], List[SocialEvent]]:
    username = (username or "").strip()
    if not username:
        return False, "username is required.", []
    other = User.objects.filter(username__iexact=username).first()
    if other is None:
        return False, "User not found.", []
    pending = FriendRequest.objects.filter(from_user=other, to_user=actor).first()
    if not pending:
        return False, "No pending friend request from this user.", []
    pending.delete()
    actor.friends.add(other)
    events: List[SocialEvent] = [
        (actor.pk, {"type": "friend_request_accepted", "username": other.username}),
        (other.pk, {"type": "friend_request_accepted", "username": actor.username}),
    ]
    return True, None, events


def friend_request_cancel(actor: User, username: str) -> Tuple[bool, Optional[str], List[SocialEvent]]:
    username = (username or "").strip()
    if not username:
        return False, "username is required.", []
    other = User.objects.filter(username__iexact=username).first()
    if other is None:
        return False, "User not found.", []
    events: List[SocialEvent] = []
    deleted = False

    if FriendRequest.objects.filter(from_user=actor, to_user=other).delete()[0]:
        deleted = True
        events.append((other.pk, {"type": "friend_request_removed", "username": actor.username}))
        events.append((actor.pk, {"type": "friend_request_removed", "username": other.username}))

    if FriendRequest.objects.filter(from_user=other, to_user=actor).delete()[0]:
        deleted = True
        events.append((other.pk, {"type": "friend_request_removed", "username": actor.username}))
        events.append((actor.pk, {"type": "friend_request_removed", "username": other.username}))

    if not deleted:
        return False, "No pending friend request with this user.", []
    return True, None, events


def friend_remove(actor: User, username: str) -> Tuple[bool, Optional[str], List[SocialEvent]]:
    """End mutual friendship (symmetrical M2M) and notify both users."""
    username = (username or "").strip()
    if not username:
        return False, "username is required.", []
    if username.lower() == actor.username.lower():
        return False, "You cannot remove yourself.", []
    other = User.objects.filter(username__iexact=username).first()
    if other is None:
        return False, "User not found.", []
    if not actor.friends.filter(pk=other.pk).exists():
        return False, "Not friends with this user.", []
    actor.friends.remove(other)
    FriendRequest.objects.filter(from_user=actor, to_user=other).delete()
    FriendRequest.objects.filter(from_user=other, to_user=actor).delete()
    events: List[SocialEvent] = [
        (actor.pk, {"type": "friend_removed", "username": other.username}),
        (other.pk, {"type": "friend_removed", "username": actor.username}),
    ]
    return True, None, events
