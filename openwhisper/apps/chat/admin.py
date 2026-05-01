from django.contrib import admin
from openwhisper.apps.chat.models import Chat

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ["id", "get_users", "get_messages", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["users__username", "users__email", "users__phone_number", "users__first_name", "users__last_name", "users__id", "id", "messages__content", "messages__id"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["users", "messages"]}),
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("users", "messages")
    
    @admin.display(description="Users")
    def get_users(self, obj):
        return ", ".join([user.username for user in obj.users.all()])
    
    @admin.display(description="Messages")
    def get_messages(self, obj):
        return obj.messages.count()