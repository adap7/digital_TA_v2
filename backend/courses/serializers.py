from rest_framework import serializers
from .models import Course
from .models import Exercise

class CourseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title"]


class CourseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title", "ai_model"]

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
