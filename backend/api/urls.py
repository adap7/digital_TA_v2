from .views import MeView
from courses.views import CourseListView
from django.urls import include, path
urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("", include("topics.urls")),
]
