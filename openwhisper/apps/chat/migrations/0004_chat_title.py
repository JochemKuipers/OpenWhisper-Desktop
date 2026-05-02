# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_remove_message_chat_sender_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="chat",
            name="title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
