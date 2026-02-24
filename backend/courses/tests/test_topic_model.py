from django.core.exceptions import ValidationError
from django.test import TestCase
from tenants.models import Tenant
from courses.models import Course
from topics.models import Topic


class TopicModelTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test University", slug="test-uni")
        self.course = Course.objects.create(
            tenant=self.tenant,
            title="Calculus I",
            code="CALC101",
        )

    def test_topic_creation(self):
        topic = Topic.objects.create(
            course=self.course,
            title="Limits",
            order_index=1,
        )

        self.assertEqual(topic.title, "Limits")
        self.assertFalse(topic.is_published)
        self.assertEqual(topic.course, self.course)

    def test_topic_ordering(self):
        Topic.objects.create(course=self.course, title="Derivatives", order_index=2)
        Topic.objects.create(course=self.course, title="Limits", order_index=1)

        topics = list(self.course.topics.all())
        self.assertEqual(topics[0].title, "Limits")
        self.assertEqual(topics[1].title, "Derivatives")

    def test_topic_with_parent(self):
        parent = Topic.objects.create(course=self.course, title="Parent", order_index=1)
        child = Topic.objects.create(course=self.course, title="Child", order_index=1, parent=parent)

        self.assertEqual(child.parent, parent)
        self.assertIn(child, list(parent.subtopics.all()))

    def test_topic_cannot_be_own_parent(self):
        topic = Topic.objects.create(course=self.course, title="Topic", order_index=1)
        topic.parent = topic

        with self.assertRaises(ValidationError):
            topic.clean()

    def test_parent_must_belong_to_same_course(self):
        other_course = Course.objects.create(tenant=self.tenant, title="Physics", code="PHY101")
        parent = Topic.objects.create(course=other_course, title="Other Parent", order_index=1)
        child = Topic(course=self.course, title="Child", order_index=1, parent=parent)

        with self.assertRaises(ValidationError):
            child.clean()
