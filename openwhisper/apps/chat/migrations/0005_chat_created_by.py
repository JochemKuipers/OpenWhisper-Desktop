import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_chat_created_by(apps, schema_editor):
    Chat = apps.get_model("chat", "Chat")
    for chat in Chat.objects.all().iterator():
        if chat.created_by_id:
            continue
        first = chat.users.order_by("id").first()
        if first:
            chat.created_by_id = first.pk
            chat.save(update_fields=["created_by_id"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0004_chat_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="chat",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="chats_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_chat_created_by, migrations.RunPython.noop),
    ]
