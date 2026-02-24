from django.db import models

from tenants.models import Tenant
from users.models import User
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

class Course(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.title}"


class CourseMembership(models.Model):
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

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user.email} → {self.course.code} ({self.role})"

class Exercise(models.Model):
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
        Enforce data integrity rules.
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