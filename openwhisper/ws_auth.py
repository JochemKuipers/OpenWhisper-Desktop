"""WebSocket auth: JWT access token from query string (?token=...)."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _user_from_id(pk: int):
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtWsAuthMiddleware(BaseMiddleware):
    """Populate scope[\"user\"] from SimpleJWT access token in the WebSocket URL."""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        scope = dict(scope)
        qs = scope.get("query_string", b"").decode()
        token = (parse_qs(qs).get("token") or [None])[0]
        user = AnonymousUser()

        if token:
            try:
                validated = AccessToken(token)
                uid = validated["user_id"]
                user = await _user_from_id(int(uid))
            except (InvalidToken, TokenError, KeyError, ValueError, TypeError):
                user = AnonymousUser()

        scope["user"] = user
        return await super().__call__(scope, receive, send)
