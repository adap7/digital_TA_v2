from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from api.mixins import TenantScopedQuerysetMixin
from .models import Course
from .serializers import CourseSerializer


class CourseListView(TenantScopedQuerysetMixin, ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
