import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0002_alter_topic_options_rename_order_topic_order_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="topic",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subtopics",
                to="topics.topic",
            ),
        ),
    ]
