from rest_framework import serializers
from .models import Course, CourseMembership, Exercise, Submission, SubmissionMessage

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
        fields = [
            "id", "exercise", "answer", "attempt_number", "is_correct", "submitted_at",
            "teacher_comment", "teacher_is_correct",
            "messages",
        ]


class SubmissionTeacherSerializer(serializers.ModelSerializer):
    messages = SubmissionMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "exercise", "student", "answer", "attempt_number", "is_correct", "submitted_at",
            "teacher_comment", "teacher_is_correct", "reviewed_by", "reviewed_at",
            "messages",
        ]


class SubmissionReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["teacher_comment", "teacher_is_correct"]


class CourseMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CourseMembership
        fields = ["id", "user", "user_email", "role", "is_super_teacher", "joined_at"]


class CourseMembershipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMembership
        fields = ["user", "role", "is_super_teacher"]


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
