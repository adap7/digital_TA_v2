from types import SimpleNamespace

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Course, Exercise, CourseMembership, Submission, SubmissionMessage
from .serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    CourseMembershipSerializer,
    CourseMembershipCreateSerializer,
    ExerciseStudentSerializer,
    ExerciseTeacherSerializer,
    SubmissionSerializer,
    SubmissionTeacherSerializer,
    SubmissionMessageSerializer,
)
from .permissions import IsTeacherOrAdmin
from .ai import evaluate_submission, get_followup_response
from users.models import UserRole

# COURSE LIST
class CourseListView(ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Course.objects.filter(tenant=user.tenant)

        return Course.objects.filter(
            tenant=user.tenant,
            memberships__user=user,
        ).distinct()

# COURSE DETAIL
class CourseDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    serializer_class = CourseDetailSerializer

    def get_queryset(self):
        return Course.objects.filter(tenant=self.request.user.tenant)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=serializer.instance,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")
        serializer.save()


# COURSE EXERCISE LIST
class CourseExerciseListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_course(self):
        return get_object_or_404(
            Course,
            id=self.kwargs["course_id"],
            tenant=self.request.user.tenant,
        )

    def get_queryset(self):
        course = self.get_course()
        user = self.request.user

        queryset = Exercise.objects.filter(course=course)

        if user.role == UserRole.STUDENT:
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).exists():
                return Exercise.objects.none()
            return queryset.filter(status=Exercise.Status.PUBLISHED)

        return queryset

    def get_serializer_class(self):
        if self.request.user.role == UserRole.STUDENT:
            return ExerciseStudentSerializer
        return ExerciseTeacherSerializer

    def perform_create(self, serializer):
        course = self.get_course()
        user = self.request.user

        # Only teacher/admin can create
        if user.role == UserRole.STUDENT:
            raise PermissionDenied("Students cannot create exercises.")

        # Teacher must belong to course
        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")

        # Topic must belong to the same course
        topic = serializer.validated_data.get('topic')
        if topic and topic.course != course:
            raise ValidationError("Topic must belong to the same course.")

        serializer.save(course=course, created_by=user)

# EXERCISE DETAIL
class ExerciseDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Exercise.objects.filter(
            course__tenant=user.tenant
        )

        if user.role == UserRole.STUDENT:
            enrolled_course_ids = CourseMembership.objects.filter(
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).values_list("course_id", flat=True)
            return queryset.filter(
                status=Exercise.Status.PUBLISHED,
                course_id__in=enrolled_course_ids,
            )

        return queryset

    def get_serializer_class(self):
        if self.request.user.role == UserRole.STUDENT:
            return ExerciseStudentSerializer
        return ExerciseTeacherSerializer

    def update(self, request, *args, **kwargs):
        if request.user.role == UserRole.STUDENT:
            return Response(status=403)

        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=serializer.instance.course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                raise PermissionDenied("Not assigned to this course.")
        super().perform_update(serializer)

# WORKFLOW
class SubmitForReviewView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )
        self.check_object_permissions(request, exercise)

        exercise.submit_for_review()
        return Response({"status": "submitted"}, status=200)


class PublishExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )
        self.check_object_permissions(request, exercise)

        exercise.publish(request.user)
        return Response({"status": "published"}, status=200)


class UnpublishExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            course__tenant=request.user.tenant,
        )
        self.check_object_permissions(request, exercise)

        exercise.unpublish(request.user)
        return Response({"status": "unpublished"}, status=200)


# SUBMISSIONS

def _check_mcq_correct(answer: dict, answer_key) -> bool | None:
    """Return True/False for MCQ, None if it can't be determined."""
    student_choice = answer.get("choice")
    if student_choice is None:
        return None
    if isinstance(answer_key, dict):
        return student_choice == answer_key.get("choice")
    if isinstance(answer_key, str):
        return student_choice == answer_key
    return None


class ExerciseSubmissionListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_exercise(self, request, exercise_id):
        return get_object_or_404(
            Exercise,
            pk=exercise_id,
            course__tenant=request.user.tenant,
        )

    def post(self, request, exercise_id):
        """Student submits an answer; AI evaluates and returns feedback."""
        user = request.user
        if user.role != UserRole.STUDENT:
            return Response({"detail": "Only students can submit answers."}, status=403)

        exercise = self._get_exercise(request, exercise_id)

        if exercise.status != Exercise.Status.PUBLISHED:
            return Response({"detail": "Exercise is not published."}, status=400)

        if not CourseMembership.objects.filter(
            course=exercise.course,
            user=user,
            role=CourseMembership.Role.STUDENT,
        ).exists():
            return Response({"detail": "Not enrolled in this course."}, status=403)

        answer = request.data.get("answer")
        if not answer or not isinstance(answer, dict):
            return Response({"detail": "answer must be a non-empty JSON object."}, status=400)

        # MCQ auto-grading
        is_correct = None
        if exercise.type == Exercise.Type.MCQ and exercise.answer_key is not None:
            is_correct = _check_mcq_correct(answer, exercise.answer_key)

        # Call AI — do NOT save anything if this fails
        try:
            ai_text = evaluate_submission(exercise, answer)
        except Exception:
            return Response(
                {"detail": "AI feedback service unavailable. Please try again later."},
                status=503,
            )

        attempt_number = Submission.objects.filter(
            exercise=exercise, student=user
        ).count() + 1

        submission = Submission.objects.create(
            exercise=exercise,
            student=user,
            answer=answer,
            attempt_number=attempt_number,
            is_correct=is_correct,
        )

        from .ai import _format_answer
        SubmissionMessage.objects.create(
            submission=submission,
            role=SubmissionMessage.Role.STUDENT,
            content=_format_answer(answer),
        )
        SubmissionMessage.objects.create(
            submission=submission,
            role=SubmissionMessage.Role.ASSISTANT,
            content=ai_text,
        )

        serializer = SubmissionSerializer(submission)
        return Response(serializer.data, status=201)

    def get(self, request, exercise_id):
        """List submissions for an exercise."""
        user = request.user
        exercise = self._get_exercise(request, exercise_id)

        if user.role == UserRole.STUDENT:
            if not CourseMembership.objects.filter(
                course=exercise.course,
                user=user,
                role=CourseMembership.Role.STUDENT,
            ).exists():
                return Response({"detail": "Not enrolled in this course."}, status=403)
            submissions = Submission.objects.filter(exercise=exercise, student=user)
            return Response(SubmissionSerializer(submissions, many=True).data)

        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=exercise.course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                return Response({"detail": "Not assigned to this course."}, status=403)

        submissions = Submission.objects.filter(exercise=exercise)
        return Response(SubmissionTeacherSerializer(submissions, many=True).data)


class SubmissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        submission = get_object_or_404(
            Submission,
            pk=pk,
            exercise__course__tenant=request.user.tenant,
        )
        user = request.user

        if user.role == UserRole.STUDENT:
            if submission.student != user:
                return Response(status=404)
            return Response(SubmissionSerializer(submission).data)

        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=submission.exercise.course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                return Response({"detail": "Not assigned to this course."}, status=403)

        return Response(SubmissionTeacherSerializer(submission).data)


class SubmissionMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Student sends a follow-up message; AI responds in context."""
        user = request.user
        if user.role != UserRole.STUDENT:
            return Response({"detail": "Only students can send follow-up messages."}, status=403)

        submission = get_object_or_404(
            Submission,
            pk=pk,
            exercise__course__tenant=user.tenant,
        )

        if submission.student != user:
            return Response(status=404)

        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "content is required."}, status=400)

        exercise = submission.exercise
        existing_messages = list(submission.messages.all())
        new_student_msg = SimpleNamespace(role=SubmissionMessage.Role.STUDENT, content=content)
        all_messages = existing_messages + [new_student_msg]

        try:
            ai_text = get_followup_response(exercise, all_messages)
        except Exception:
            return Response(
                {"detail": "AI feedback service unavailable. Please try again later."},
                status=503,
            )

        SubmissionMessage.objects.create(
            submission=submission,
            role=SubmissionMessage.Role.STUDENT,
            content=content,
        )
        ai_message = SubmissionMessage.objects.create(
            submission=submission,
            role=SubmissionMessage.Role.ASSISTANT,
            content=ai_text,
        )

        return Response(SubmissionMessageSerializer(ai_message).data, status=201)


# MEMBERSHIP MANAGEMENT

def _is_super_teacher_of(user, course):
    """True if user is a teacher assigned to course with is_super_teacher=True."""
    return CourseMembership.objects.filter(
        user=user,
        course=course,
        role=CourseMembership.Role.TEACHER,
        is_super_teacher=True,
    ).exists()


class CourseMemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_course(self, request, course_id):
        return get_object_or_404(
            Course,
            id=course_id,
            tenant=request.user.tenant,
        )

    def get(self, request, course_id):
        user = request.user
        course = self._get_course(request, course_id)

        if user.role == UserRole.STUDENT:
            return Response(status=403)

        if user.role == UserRole.TEACHER:
            if not CourseMembership.objects.filter(
                course=course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists():
                return Response({"detail": "Not assigned to this course."}, status=403)

        memberships = CourseMembership.objects.filter(course=course).select_related("user")
        return Response(CourseMembershipSerializer(memberships, many=True).data)

    def post(self, request, course_id):
        user = request.user
        course = self._get_course(request, course_id)

        is_admin = user.role == UserRole.ADMIN
        is_super = _is_super_teacher_of(user, course)

        if not is_admin and not is_super:
            return Response({"detail": "Only admins or super teachers can manage members."}, status=403)

        serializer = CourseMembershipCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        target_user = serializer.validated_data["user"]
        role = serializer.validated_data["role"]
        wants_super = serializer.validated_data.get("is_super_teacher", False)

        # Tenant check
        if target_user.tenant != course.tenant:
            return Response({"detail": "User does not belong to this tenant."}, status=400)

        # Super teachers cannot grant super teacher status
        if not is_admin and wants_super:
            return Response({"detail": "Only admins can assign super teacher status."}, status=403)

        try:
            membership = CourseMembership.objects.create(
                user=target_user,
                course=course,
                role=role,
                is_super_teacher=wants_super if is_admin else False,
            )
        except Exception:
            return Response({"detail": "Membership already exists."}, status=400)

        return Response(CourseMembershipSerializer(membership).data, status=201)


class CourseMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_course(self, request, course_id):
        return get_object_or_404(
            Course,
            id=course_id,
            tenant=request.user.tenant,
        )

    def delete(self, request, course_id, pk):
        user = request.user
        course = self._get_course(request, course_id)

        is_admin = user.role == UserRole.ADMIN
        is_super = _is_super_teacher_of(user, course)

        if not is_admin and not is_super:
            return Response({"detail": "Only admins or super teachers can remove members."}, status=403)

        membership = get_object_or_404(CourseMembership, pk=pk, course=course)

        # Super teachers can only remove students, not teachers
        if not is_admin and membership.role != CourseMembership.Role.STUDENT:
            return Response({"detail": "Super teachers can only remove students."}, status=403)

        membership.delete()
        return Response(status=204)
