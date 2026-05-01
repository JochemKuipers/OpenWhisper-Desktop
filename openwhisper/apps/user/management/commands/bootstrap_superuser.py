"""Create or reset the local/dev superuser (usable password for admin + api-auth)."""

from __future__ import annotations

import environ
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

env = environ.Env()


class Command(BaseCommand):
    help = (
        "Create or reset superuser credentials for development. "
        "Reads OPENWHISPER_DEV_SUPERUSER_USERNAME, EMAIL, PASSWORD "
        "(defaults: admin / admin@example.com / admin)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default=None)
        parser.add_argument("--email", type=str, default=None)
        parser.add_argument("--password", type=str, default=None)

    def handle(self, *args, **options):
        environ.Env.read_env()

        username = options["username"] or env.str(
            "OPENWHISPER_DEV_SUPERUSER_USERNAME",
            default="admin",
        )
        email = options["email"] or env.str(
            "OPENWHISPER_DEV_SUPERUSER_EMAIL",
            default="admin@example.com",
        )
        password = options["password"] or env.str(
            "OPENWHISPER_DEV_SUPERUSER_PASSWORD",
            default="admin",
        )

        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created superuser {username!r} ({email})."),
            )
            return

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(f"Updated superuser {username!r} ({email}); password reset."),
        )
