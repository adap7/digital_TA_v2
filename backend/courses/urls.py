from django.urls import path
from .views import CourseExerciseListView, CourseMemberListView, CourseMemberDetailView, CourseProgressView

urlpatterns = [
    path("<int:course_id>/exercises/", CourseExerciseListView.as_view()),
    path("<int:course_id>/members/", CourseMemberListView.as_view()),
    path("<int:course_id>/members/<int:pk>/", CourseMemberDetailView.as_view()),
    path("<int:course_id>/progress/", CourseProgressView.as_view()),
]