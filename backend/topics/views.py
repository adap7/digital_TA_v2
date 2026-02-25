from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from courses.models import Course, CourseMembership
from .models import Topic
from .serializers import TopicSerializer, TopicCreateSerializer


class TopicListCreateView(ListCreateAPIView):
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
        qs = Topic.objects.filter(course=course)

        if user.role == "student":
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).exists():
                return Topic.objects.none()
            qs = qs.filter(is_published=True)

        parent_param = self.request.query_params.get("parent")
        if parent_param is not None:
            if parent_param.lower() == "null":
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent_id=parent_param)

        return qs.order_by("order_index", "created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TopicCreateSerializer
        return TopicSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ["teacher", "admin"]:
            self.permission_denied(self.request)

        course = self.get_course()

        if user.role == "teacher":
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")

        parent = serializer.validated_data.get("parent")
        if parent and parent.course_id != course.id:
            raise ValidationError({"parent": "Parent topic must belong to the same course."})

        serializer.save(course=course)


class TopicDetailUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Topic.objects.filter(course__tenant=user.tenant)

        if user.role == "student":
            enrolled_course_ids = CourseMembership.objects.filter(
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).values_list("course_id", flat=True)
            return qs.filter(
                is_published=True,
                course_id__in=enrolled_course_ids,
            )

        return qs

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return TopicCreateSerializer
        return TopicSerializer

    def update(self, request, *args, **kwargs):
        if request.user.role == "student":
            return Response(status=403)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == "teacher":
            if not CourseMembership.objects.filter(
                course=serializer.instance.course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")

        parent = serializer.validated_data.get("parent")
        if parent and parent.course_id != serializer.instance.course_id:
            raise ValidationError({"parent": "Parent topic must belong to the same course."})

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role == "student":
            return Response(status=403)

        instance = self.get_object()

        if request.user.role == "teacher":
            if not CourseMembership.objects.filter(
                course=instance.course,
                user=request.user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")

        self.perform_destroy(instance)
        return Response(status=204)
