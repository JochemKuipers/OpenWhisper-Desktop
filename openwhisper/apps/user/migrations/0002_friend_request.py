# Generated manually for FriendRequest model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FriendRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "from_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="friend_requests_sent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "to_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="friend_requests_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_friend_requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="friendrequest",
            constraint=models.UniqueConstraint(
                fields=("from_user", "to_user"),
                name="unique_friend_request_direction",
            ),
        ),
        migrations.AddIndex(
            model_name="friendrequest",
            index=models.Index(fields=["to_user", "-created_at"], name="user_fr_to_user_created_desc_idx"),
        ),
        migrations.AddIndex(
            model_name="friendrequest",
            index=models.Index(fields=["from_user", "-created_at"], name="user_fr_from_user_created_desc_idx"),
        ),
    ]
