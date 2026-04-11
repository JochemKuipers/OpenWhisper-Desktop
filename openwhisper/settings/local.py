from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

INSTALLED_APPS += ["django_browser_reload", "debug_toolbar"]

MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware", "debug_toolbar.middleware.DebugToolbarMiddleware"]

INTERNAL_IPS = [
    "127.0.0.1",
]