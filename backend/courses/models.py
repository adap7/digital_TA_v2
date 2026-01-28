from django.db import models

from tenants.models import Tenant
from users.models import User


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

class Topic(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics",
    )

    title = models.CharField(max_length=255)

    order_index = models.PositiveIntegerField()

    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order_index"]
        unique_together = ("course", "order_index")

    def __str__(self):
        return f"{self.course.code} — {self.title}"
