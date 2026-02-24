from django.urls import path
from .views import (
    CourseExerciseListView,
    ExerciseDetailView,
    SubmitForReviewView,
    PublishExerciseView,
)

urlpatterns = [
    path("<int:course_id>/exercises/", CourseExerciseListView.as_view()),
    path("exercises/<int:pk>/", ExerciseDetailView.as_view()),
    path("exercises/<int:pk>/submit-for-review/", SubmitForReviewView.as_view()),
    path("exercises/<int:pk>/publish/", PublishExerciseView.as_view()),
]