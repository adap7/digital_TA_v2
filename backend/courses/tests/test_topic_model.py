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
