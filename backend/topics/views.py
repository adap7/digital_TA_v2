from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from courses.models import Course
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

        qs = Topic.objects.filter(course=course)

        # Students only see published topics
        if self.request.user.role == "student":
            qs = qs.filter(is_published=True)

        # Optional ?parent= filter: "null" → top-level, integer → subtopics of that parent
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
        if self.request.user.role not in ["teacher", "admin"]:
            self.permission_denied(self.request)

        course = self.get_course()
        parent = serializer.validated_data.get("parent")
        if parent and parent.course_id != course.id:
            raise ValidationError({"parent": "Parent topic must belong to the same course."})

        serializer.save(course=course)



