from django.db import models
from django.core.exceptions import ValidationError
from courses.models import Course


class Topic(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics",
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subtopics",
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    order_index = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError("A topic cannot be its own parent.")
        if self.parent_id and self.parent.course_id != self.course_id:
            raise ValidationError("Parent topic must belong to the same course.")

    class Meta:
        ordering = ["order_index", "created_at"]

    def __str__(self):
        return self.title
