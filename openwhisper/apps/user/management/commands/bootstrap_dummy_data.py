"""Seed users, chats, and messages for local API / model testing."""

from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count

from openwhisper.apps.chat.models import Chat, Message

DUMMY_USERNAME_PREFIX = "dummy_"


class Command(BaseCommand):
    help = (
        "Create repeatable dummy users (username prefix %(prefix)s), friendships, chats, "
        "and messages. Safe to run multiple times; refreshes dummy-only chats/messages. "
        "Use --purge to remove all dummy users and related rows."
    ) % {"prefix": DUMMY_USERNAME_PREFIX}

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default="dummy123",
            help="Password for dummy accounts (default: dummy123).",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help=f"Delete users whose username starts with {DUMMY_USERNAME_PREFIX!r}, "
            "then exit without seeding.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        password = options["password"]

        if options["purge"]:
            self._purge_dummy_users(User)
            return

        users = self._ensure_dummy_users(User, password)
        alice, bob, carol = users["alice"], users["bob"], users["carol"]

        alice.friends.set([bob, carol])
        bob.friends.set([alice, carol])
        carol.friends.set([alice, bob])

        self._reset_dummy_only_chats(list(users.values()))

        chat_ab = Chat.objects.create(created_by=alice)
        chat_ab.users.add(alice, bob)
        Message.objects.update_or_create(
            chat=chat_ab,
            sender=alice,
            defaults={"content": "Hey Bob — grabbing coffee later?"},
        )
        Message.objects.update_or_create(
            chat=chat_ab,
            sender=bob,
            defaults={"content": "Sounds good, ping me when you're free."},
        )

        chat_abc = Chat.objects.create(created_by=alice)
        chat_abc.users.add(alice, bob, carol)
        Message.objects.update_or_create(
            chat=chat_abc,
            sender=carol,
            defaults={"content": "Team sync moved to 3pm."},
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Dummy data ready: users dummy_alice, dummy_bob, dummy_carol "
                f"(password: {password!r}). "
                "Log in via session auth or token setup to hit /api/users/."
            ),
        )

    def _purge_dummy_users(self, User):
        qs = User.objects.filter(username__startswith=DUMMY_USERNAME_PREFIX)
        count = qs.count()
        dummy_ids = set(qs.values_list("pk", flat=True))

        for chat in Chat.objects.filter(users__pk__in=dummy_ids).distinct():
            participant_ids = set(chat.users.values_list("pk", flat=True))
            if participant_ids <= dummy_ids:
                chat.delete()

        qs.delete()

        orphaned = Chat.objects.annotate(user_count=Count("users")).filter(user_count=0)
        orphaned.delete()

        self.stdout.write(self.style.WARNING(f"Removed {count} dummy user(s) and linked chats."))

    def _ensure_dummy_users(self, User, password: str):
        specs = [
            {
                "key": "alice",
                "username": f"{DUMMY_USERNAME_PREFIX}alice",
                "email": "alice@dummy.openwhisper.test",
                "phone_number": "1000000001",
                "first_name": "Alice",
                "last_name": "Dummy",
                "bio": "Seed account for API tests.",
                "location": "Amsterdam",
                "gender": "female",
                "birth_date": date(1992, 3, 15),
            },
            {
                "key": "bob",
                "username": f"{DUMMY_USERNAME_PREFIX}bob",
                "email": "bob@dummy.openwhisper.test",
                "phone_number": "1000000002",
                "first_name": "Bob",
                "last_name": "Dummy",
                "bio": "Second fixture user.",
                "location": "Utrecht",
                "gender": "male",
                "birth_date": date(1988, 7, 22),
            },
            {
                "key": "carol",
                "username": f"{DUMMY_USERNAME_PREFIX}carol",
                "email": "carol@dummy.openwhisper.test",
                "phone_number": "1000000003",
                "first_name": "Carol",
                "last_name": "Dummy",
                "bio": "Third fixture user.",
                "location": "Rotterdam",
                "gender": "other",
                "birth_date": date(1995, 11, 30),
            },
        ]

        out: dict[str, object] = {}
        for row in specs:
            spec = row.copy()
            key = spec.pop("key")
            username = spec.pop("username")
            email = spec.pop("email")

            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    **spec,
                )
                created = True
            else:
                user.email = email
                user.phone_number = spec["phone_number"]
                user.first_name = spec["first_name"]
                user.last_name = spec["last_name"]
                user.bio = spec["bio"]
                user.location = spec["location"]
                user.gender = spec["gender"]
                user.birth_date = spec["birth_date"]
                user.set_password(password)
                user.save(update_fields=[
                    "email",
                    "phone_number",
                    "first_name",
                    "last_name",
                    "bio",
                    "location",
                    "gender",
                    "birth_date",
                    "password",
                    "updated_at",
                ])
                created = False

            label = "Created" if created else "Updated"
            self.stdout.write(f"  {label} user {username!r}")
            out[key] = user

        return out

    def _reset_dummy_only_chats(self, dummy_users):
        dummy_ids = {u.pk for u in dummy_users}
        for chat in Chat.objects.filter(users__pk__in=dummy_ids).distinct():
            participant_ids = set(chat.users.values_list("pk", flat=True))
            if participant_ids <= dummy_ids:
                chat.delete()
