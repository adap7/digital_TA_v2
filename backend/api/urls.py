from .views import MeView
from courses.views import (
    CourseListView,
    CourseDetailView,
    ExerciseDetailView,
    SubmitForReviewView,
    PublishExerciseView,
    UnpublishExerciseView,
    ExerciseSubmissionListView,
    SubmissionDetailView,
    SubmissionMessageView,
    SubmissionReviewView,
)
from django.urls import include, path

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("", include("topics.urls")),
    path("courses/", include("courses.urls")),
    path("exercises/<int:pk>/", ExerciseDetailView.as_view()),
    path("exercises/<int:pk>/submit-for-review/", SubmitForReviewView.as_view()),
    path("exercises/<int:pk>/publish/", PublishExerciseView.as_view()),
    path("exercises/<int:pk>/unpublish/", UnpublishExerciseView.as_view()),
    path("exercises/<int:exercise_id>/submissions/", ExerciseSubmissionListView.as_view()),
    path("submissions/<int:pk>/", SubmissionDetailView.as_view()),
    path("submissions/<int:pk>/messages/", SubmissionMessageView.as_view()),
    path("submissions/<int:pk>/review/", SubmissionReviewView.as_view()),
]
