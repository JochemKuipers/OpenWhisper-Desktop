import os

# Ensure base settings can import without a real Postgres .env during pytest.
_env = os.environ
_env.setdefault("SECRET_KEY", "test-secret-not-for-production")
for _key, _val in (
    ("DB_NAME", "unused"),
    ("DB_USER", "unused"),
    ("DB_PASSWORD", "unused"),
    ("DB_HOST", "localhost"),
):
    _env.setdefault(_key, _val)

from .base import *

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
