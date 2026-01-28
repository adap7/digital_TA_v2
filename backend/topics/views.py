from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from courses.models import Course
from .models import Topic
from .serializers import TopicSerializer, TopicCreateSerializer
from .permissions import IsTeacherOrAdmin

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

        return qs.order_by("order_index", "created_at")
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return TopicCreateSerializer
        return TopicSerializer
    
    def perform_create(self, serializer):
        if self.request.user.role not in ["teacher", "admin"]:
            self.permission_denied(self.request)

        serializer.save(course=self.get_course())



