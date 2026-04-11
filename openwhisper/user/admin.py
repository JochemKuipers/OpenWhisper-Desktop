from django.contrib import admin
from openwhisper.user.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'contact_number', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'contact_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        (None, {'fields': ['username', 'email', 'contact_number']}),
        ('Profile', {'fields': ['avatar', 'bio', 'birth_date', 'gender', 'location', 'website']}),
    ]