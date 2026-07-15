from django.contrib import admin

from app.models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "active", "can_switch_user", "created_at")
    search_fields = ("email", "name")
    list_filter = ("active", "can_switch_user")
    readonly_fields = ("created_at", "updated_at")
