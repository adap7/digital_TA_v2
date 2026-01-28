from django.urls import path
from .views import TopicListCreateView

urlpatterns = [
    path(
        "courses/<int:course_id>/topics/",
        TopicListCreateView.as_view(),
        name="course-topics",
    ),
]
