from django.contrib import admin
from openwhisper.apps.user.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "username",
        "email",
        "phone_number",
        "is_active",
        "is_staff",
        "is_superuser",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["username", "email", "phone_number"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["username", "email", "phone_number"]}),
        (
            "Profile",
            {
                "fields": [
                    "avatar",
                    "bio",
                    "birth_date",
                    "gender",
                    "location",
                ]
            },
        ),
    ]
