"""
ASGI config for openwhisper project.

HTTP is served by Django; WebSockets use Django Channels (see openwhisper.routing).
Run with Daphne, e.g. ``daphne -b 127.0.0.1 -p 8000 openwhisper.asgi:application``.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openwhisper.settings.local")

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
