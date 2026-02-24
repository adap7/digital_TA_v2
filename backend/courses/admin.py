from django.contrib import admin
from .models import Course, CourseMembership, Exercise, Submission, SubmissionMessage

admin.site.register(Course)
admin.site.register(CourseMembership)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "type", "status", "created_by", "created_at"]
    list_filter = ["status", "type", "course__tenant"]
    search_fields = ["title", "prompt"]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["student", "exercise", "attempt_number", "is_correct", "submitted_at"]
    list_filter = ["is_correct", "exercise__course__tenant"]
    search_fields = ["student__email"]


@admin.register(SubmissionMessage)
class SubmissionMessageAdmin(admin.ModelAdmin):
    list_display = ["submission", "role", "created_at"]
    list_filter = ["role"]
