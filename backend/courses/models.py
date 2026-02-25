"""
    Course + exercise + submission domain models.

    This module implements a multi-tenant academic platform where:
        - Courses belong to tenants
        - Exercises belong to courses
        - Students submit answers with AI evaluation
        - Teachers can override AI grading

    Security invariants:
        - Cross-tenant relations are forbidden
        - Students can only access their own submissions
        - Teachers can access submissions within assigned courses
        - AI answer_key must never be exposed to students
"""
from django.db import models

from tenants.models import Tenant
from users.models import User
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

class AiModel(models.TextChoices):
    """
        Defines which LLM provider a course uses for exercise evaluation.
        This allows per-course AI strategy selection and future provider expansion.
    """
    CLAUDE   = "claude-sonnet-4-6", "Claude Sonnet (Anthropic)"
    GPT4O    = "gpt-4o",            "GPT-4o (OpenAI)"
    DEEPSEEK = "deepseek-chat",     "DeepSeek Chat"


class Course(models.Model):
    """
        Represents a tenant-scoped course.
        Tenant isolation rule:
            - All related objects (memberships, exercises, submissions) must belong to the same tenant as the course.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    title    = models.CharField(max_length=255)
    code     = models.CharField(max_length=50)
    ai_model = models.CharField(
        max_length=50,
        choices=AiModel.choices,
        default=AiModel.CLAUDE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.title}"


class CourseMembership(models.Model):
    """
        Maps users to courses with role-based permissions.
        Roles:
            - student: can submit answers and view own submissions
            - teacher: can create/review exercises and review submissions

        Constraint:
            - A user may have only one membership per course.
    """
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_memberships",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )
    is_super_teacher = models.BooleanField(default=False)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user.email} → {self.course.code} ({self.role})"

class Exercise(models.Model):
    """
        Represents a learning activity inside a course.
        Lifecycle: draft → in_review → published
        Key design rules:
            - MCQ exercises must define choices and answer_key
            - Non-MCQ exercises must not define choices
            - Reviewer must belong to same tenant
            - Creator must belong to same tenant
            - Topic must belong to the same course
    """
    # ENUMS
    class Type(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        FREE_TEXT = "free_text", "Free Text"
        LATEX = "latex", "Latex"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        PUBLISHED = "published", "Published"

    # RELATIONS
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="exercises",
    )

    topic = models.ForeignKey(
        "topics.Topic",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exercises",
    )

    # CORE FIELDS
    title = models.CharField(max_length=255, blank=True)

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    prompt = models.TextField()

    choices = models.JSONField(null=True, blank=True)
    answer_key = models.JSONField(null=True, blank=True)

    difficulty = models.PositiveSmallIntegerField(default=1)
    order_index = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # AUDIT FIELDS
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_exercises",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_exercises",
    )

    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # VALIDATION
    def clean(self):
        """
            Enforces domain integrity and tenant safety.
            Note:
                Validation here protects against accidental misuse but should be complemented with serializer/view-level permission checks.
        """
        # MCQ must have choices
        if self.type == self.Type.MCQ and not self.choices:
            raise ValidationError("MCQ exercises must define choices.")

        # Non-MCQ must not have choices
        if self.type != self.Type.MCQ and self.choices:
            raise ValidationError("Only MCQ exercises may define choices.")

        # Ensure reviewer is same tenant
        if self.reviewed_by and self.reviewed_by.tenant != self.course.tenant:
            raise ValidationError("Reviewer must belong to same tenant.")

        # Ensure creator belongs to same tenant
        if self.created_by.tenant != self.course.tenant:
            raise ValidationError("Creator must belong to same tenant.")

        # Ensure topic belongs to the same course
        if self.topic and self.topic.course != self.course:
            raise ValidationError("Topic must belong to the same course as the exercise.")

    # WORKFLOW METHODS
    def submit_for_review(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft exercises can be submitted for review.")

        self.status = self.Status.IN_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def publish(self, reviewer):
        """
            Publishes an exercise after review.
            Security:
                - Cross-tenant publishing is forbidden
            Workflow invariant:
                - Only exercises in IN_REVIEW state can be published
        """
        if self.status != self.Status.IN_REVIEW:
            raise ValidationError("Exercise must be in review before publishing.")

        if reviewer.tenant != self.course.tenant:
            raise ValidationError("Cross-tenant publish forbidden.")

        self.status = self.Status.PUBLISHED
        self.reviewed_by = reviewer
        self.published_at = timezone.now()

        self.save(update_fields=["status", "reviewed_by", "published_at", "updated_at"])

    def unpublish(self, reviewer):
        if self.status != self.Status.PUBLISHED:
            raise ValidationError("Only published exercises can be unpublished.")

        if reviewer.tenant != self.course.tenant:
            raise ValidationError("Cross-tenant unpublish forbidden.")

        self.status = self.Status.DRAFT
        self.published_at = None
        self.reviewed_by = reviewer

        self.save(update_fields=["status", "published_at", "reviewed_by", "updated_at"])

    # META CONFIG
    class Meta:
        ordering = ["order_index", "created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["course", "order_index"],
                name="unique_exercise_order_per_course"
            )
        ]

        indexes = [
            models.Index(fields=["course", "status"]),
            models.Index(fields=["course", "order_index"]),
            models.Index(fields=["created_by"]),
        ]

    # REPRESENTATION
    def __str__(self):
        return f"{self.course.code} — {self.title or 'Exercise'}"


class Submission(models.Model):
    """
        Represents a student's attempt to answer an exercise.
        Features:
            - Multiple attempts allowed
            - AI grading stored in is_correct
            - Teacher review can override AI grading
            - Multi-turn AI conversation stored in SubmissionMessage
        Security invariant:
            - Student and exercise must belong to same tenant
    """
    # RELATIONS
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    # ANSWER
    answer = models.JSONField()

    # GRADING
    attempt_number = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    # TEACHER REVIEW
    # These fields allow human override of AI grading.
    # AI grading remains stored and is never deleted.
    teacher_comment = models.TextField(blank=True, default="")
    teacher_is_correct = models.BooleanField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # VALIDATION
    def clean(self):
        if self.student.tenant != self.exercise.course.tenant:
            raise ValidationError("Student and exercise must belong to the same tenant.")

    # META CONFIG
    class Meta:
        ordering = ["submitted_at"]
        indexes = [
            models.Index(fields=["exercise", "student"]),
            models.Index(fields=["student"]),
        ]

    # REPRESENTATION
    def __str__(self):
        return f"Submission #{self.attempt_number} by {self.student.email} on {self.exercise}"


class SubmissionMessage(models.Model):
    """
        Stores conversation between student and AI tutor for a submission.
        Messages are append-only and ordered chronologically to preserve full conversation history for LLM context.
    """
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ASSISTANT = "assistant", "Assistant"

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] on submission {self.submission_id}"