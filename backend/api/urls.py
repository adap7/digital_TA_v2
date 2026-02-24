from .views import MeView
from courses.views import (
    CourseListView,
    ExerciseDetailView,
    SubmitForReviewView,
    PublishExerciseView,
    UnpublishExerciseView,
)
from django.urls import include, path

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("", include("topics.urls")),
    path("courses/", include("courses.urls")),
    path("exercises/<int:pk>/", ExerciseDetailView.as_view()),
    path("exercises/<int:pk>/submit-for-review/", SubmitForReviewView.as_view()),
    path("exercises/<int:pk>/publish/", PublishExerciseView.as_view()),
    path("exercises/<int:pk>/unpublish/", UnpublishExerciseView.as_view()),
]
