from django.db import models
from tenants.models import Tenant


class Course(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title
