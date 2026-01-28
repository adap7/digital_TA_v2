from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Course
from .serializers import CourseListSerializer
from users.models import UserRole


class CourseListView(ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin: all courses in tenant
        if user.role == UserRole.ADMIN:
            return Course.objects.filter(tenant=user.tenant)

        # Teacher or Student: only assigned courses
        return Course.objects.filter(
            tenant=user.tenant,
            memberships__user=user,
        ).distinct()
