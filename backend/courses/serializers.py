from rest_framework import serializers
from .models import Course, Exercise, Submission, SubmissionMessage

class CourseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title"]


class CourseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title", "ai_model"]

class SubmissionMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionMessage
        fields = ["id", "role", "content", "created_at"]


class SubmissionSerializer(serializers.ModelSerializer):
    messages = SubmissionMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "exercise", "answer", "attempt_number", "is_correct", "submitted_at", "messages"]


class SubmissionTeacherSerializer(serializers.ModelSerializer):
    messages = SubmissionMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "exercise", "student", "answer", "attempt_number", "is_correct", "submitted_at", "messages"]


class ExerciseStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "id",
            "course",
            "topic",
            "title",
            "type",
            "prompt",
            "choices",
            "difficulty",
            "order_index",
            "status",
            "published_at",
        ]


class ExerciseTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = "__all__"
