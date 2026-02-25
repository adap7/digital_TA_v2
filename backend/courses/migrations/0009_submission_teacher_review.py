import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0008_coursemembership_is_super_teacher"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="teacher_comment",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="submission",
            name="teacher_is_correct",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_submissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
