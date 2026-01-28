from django.urls import path
from .views import MeView
from courses.views import CourseListView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("courses/", CourseListView.as_view(), name="course-list"),
]
