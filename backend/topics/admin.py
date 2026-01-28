from django.contrib import admin
from .models import Topic

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "is_published", "order_index")
    list_filter = ("is_published",)
    ordering = ("course", "order_index")

