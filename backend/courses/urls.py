from django.urls import path
from .views import CourseExerciseListView

urlpatterns = [
    path("<int:course_id>/exercises/", CourseExerciseListView.as_view()),
]