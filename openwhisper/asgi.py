"""
ASGI config for openwhisper project.

HTTP is served by Django; WebSockets use Django Channels (see openwhisper.routing).
Run with Daphne, e.g. ``daphne -b 127.0.0.1 -p 8000 openwhisper.asgi:application``.
"""

import os
import socket
from urllib.parse import urlparse

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openwhisper.settings.local")


def _extract_redis_host_port(host_entry):
    if isinstance(host_entry, tuple):
        host = host_entry[0]
        port = host_entry[1] if len(host_entry) > 1 else 6379
        return host, int(port)

    if isinstance(host_entry, str):
        if "://" in host_entry:
            parsed = urlparse(host_entry)
            return parsed.hostname or "localhost", parsed.port or 6379
        return host_entry, 6379

    raise ValueError(f"Unsupported Redis host config: {host_entry!r}")


def _assert_redis_available_for_channels() -> None:
    """Fail fast during ASGI startup when channels_redis cannot be reached."""
    layer_config = settings.CHANNEL_LAYERS.get("default", {})
    backend = layer_config.get("BACKEND", "")
    if backend != "channels_redis.core.RedisChannelLayer":
        return

    hosts = layer_config.get("CONFIG", {}).get("hosts", [])
    if not hosts:
        raise RuntimeError("CHANNEL_LAYERS is configured for Redis, but no Redis hosts are set.")

    host, port = _extract_redis_host_port(hosts[0])
    try:
        with socket.create_connection((host, port), timeout=1.5):
            pass
    except OSError as exc:
        raise RuntimeError(
            "Redis is required for realtime chat, but it is unreachable at "
            f"{host}:{port}. Start Redis (e.g. `sudo systemctl start redis`) "
            "and restart the app."
        ) from exc


_assert_redis_available_for_channels()

django_asgi_app = get_asgi_application()

from openwhisper.routing import websocket_urlpatterns
from openwhisper.ws_auth import JwtWsAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JwtWsAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
