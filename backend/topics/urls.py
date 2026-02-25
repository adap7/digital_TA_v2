from django.urls import path
from .views import TopicListCreateView, TopicDetailUpdateDestroyView

urlpatterns = [
    path(
        "courses/<int:course_id>/topics/",
        TopicListCreateView.as_view(),
        name="course-topics",
    ),
    path(
        "topics/<int:pk>/",
        TopicDetailUpdateDestroyView.as_view(),
        name="topic-detail",
    ),
]
