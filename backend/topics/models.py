from django.db import models
from courses.models import Course


class Topic(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics",
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    order_index = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order_index", "created_at"]

    def __str__(self):
        return self.title
