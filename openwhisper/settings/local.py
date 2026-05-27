from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

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

INSTALLED_APPS += ["django_browser_reload", "debug_toolbar", "django_check_seo"]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = [
    "127.0.0.1",
]

ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost", "127.0.0.1", "testserver"]

# django-check-seo: ignore chrome that is not page content (incl. debug toolbar in dev).
DJANGO_CHECK_SEO_EXCLUDE_CONTENT = (
    "header, footer, nav, #djdt, [id^='djdt'], .djdt-hidden, #djDebugToolbarHandle"
)

# Landing is a product page, not a 600-word article.
DJANGO_CHECK_SEO_SETTINGS = {
    "content_words_number": [300, 400],
}