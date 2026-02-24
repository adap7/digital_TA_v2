from django.contrib import admin
from .models import Course, CourseMembership, Exercise

admin.site.register(Course)
admin.site.register(CourseMembership)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "type", "status", "created_by", "created_at"]
    list_filter = ["status", "type", "course__tenant"]
    search_fields = ["title", "prompt"]
