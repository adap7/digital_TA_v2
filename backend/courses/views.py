from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Course, Exercise, CourseMembership
from .serializers import (
    CourseListSerializer,
    ExerciseStudentSerializer,
    ExerciseTeacherSerializer,
)
from .permissions import IsTeacherOrAdmin
from users.models import UserRole

# COURSE LIST
class CourseListView(ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Course.objects.filter(tenant=user.tenant)

        return Course.objects.filter(
            tenant=user.tenant,
            memberships__user=user,
        ).distinct()

# COURSE EXERCISE LIST
class CourseExerciseListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_course(self):
        return get_object_or_404(
            Course,
            id=self.kwargs["course_id"],
            tenant=self.request.user.tenant,
        )

    def get_queryset(self):
        course = self.get_course()
        user = self.request.user

        queryset = Exercise.objects.filter(course=course)

        if user.role == UserRole.STUDENT:
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).exists():
                return Exercise.objects.none()
            return queryset.filter(status=Exercise.Status.PUBLISHED)

        return queryset

    def get_serializer_class(self):
        if self.request.user.role == UserRole.STUDENT:
            return ExerciseStudentSerializer
        return ExerciseTeacherSerializer

    def perform_create(self, serializer):
        course = self.get_course()
        user = self.request.user

        # Only teacher/admin can create
        if user.role == UserRole.STUDENT:
            raise PermissionDenied("Students cannot create exercises.")

        # Teacher must belong to course
        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")

        # Topic must belong to the same course
        topic = serializer.validated_data.get('topic')
        if topic and topic.course != course:
            raise ValidationError("Topic must belong to the same course.")

        serializer.save(course=course, created_by=user)

# EXERCISE DETAIL
class ExerciseDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Exercise.objects.filter(
            course__tenant=user.tenant
        )

        if user.role == UserRole.STUDENT:
            enrolled_course_ids = CourseMembership.objects.filter(
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).values_list("course_id", flat=True)
            return queryset.filter(
                status=Exercise.Status.PUBLISHED,
                course_id__in=enrolled_course_ids,
            )

        return queryset

    def get_serializer_class(self):
        if self.request.user.role == UserRole.STUDENT:
            return ExerciseStudentSerializer
        return ExerciseTeacherSerializer

    def update(self, request, *args, **kwargs):
        if request.user.role == UserRole.STUDENT:
            return Response(status=403)

        return super().update(request, *args, **kwargs)

# WORKFLOW
class SubmitForReviewView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )

        exercise.submit_for_review()
        return Response({"status": "submitted"}, status=200)


class PublishExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )

        exercise.publish(request.user)
        return Response({"status": "published"}, status=200)


class UnpublishExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )

        exercise.unpublish(request.user)
        return Response({"status": "unpublished"}, status=200)
