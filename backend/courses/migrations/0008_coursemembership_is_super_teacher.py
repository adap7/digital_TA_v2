from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0007_course_ai_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursemembership",
            name="is_super_teacher",
            field=models.BooleanField(default=False),
        ),
    ]
