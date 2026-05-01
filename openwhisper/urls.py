"""
URL configuration for openwhisper project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path
from django.conf import settings

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include("openwhisper.apps.theme.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("openwhisper.apps.api.urls")),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]


if settings.DEBUG:
    # runserver wraps StaticFilesHandler; ASGI servers (e.g. Daphne) do not.
    urlpatterns += staticfiles_urlpatterns()
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns += [
            path("__reload__/", include("django_browser_reload.urls")),
        ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        from debug_toolbar.toolbar import debug_toolbar_urls

        urlpatterns += debug_toolbar_urls()
