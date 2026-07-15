from django.contrib import admin

from app.models import Poem


@admin.register(Poem)
class PoemAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "collection", "position", "active", "created_at")
    list_filter = ("active", "author", "collection")
    search_fields = ("title", "comment")
    ordering = ("collection", "position")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("author", "collection")
