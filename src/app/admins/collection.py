from django.contrib import admin

from app.models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "position", "active", "created_at")
    list_filter = ("active", "author")
    search_fields = ("title", "comment")
    ordering = ("position",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("author",)
