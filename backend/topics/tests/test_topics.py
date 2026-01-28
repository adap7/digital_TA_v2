from rest_framework.test import APITestCase
from django.urls import reverse

from users.models import User
from tenants.models import Tenant
from courses.models import Course, CourseMembership
from topics.models import Topic


class TopicVisibilityTest(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test", slug="test")

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="pass",
            role="teacher",
            tenant=self.tenant,
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            password="pass",
            role="student",
            tenant=self.tenant,
        )

        self.course = Course.objects.create(
            tenant=self.tenant,
            title="Math",
            code="MATH101",
        )

        CourseMembership.objects.create(
            user=self.teacher,
            course=self.course,
            role="teacher",
        )

        CourseMembership.objects.create(
            user=self.student,
            course=self.course,
            role="student",
        )

        Topic.objects.create(
            course=self.course,
            title="Published",
            is_published=True,
        )

        Topic.objects.create(
            course=self.course,
            title="Draft",
            is_published=False,
        )

    def test_student_sees_only_published_topics(self):
        self.client.login(email="student@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/"
        response = self.client.get(url)

        self.assertEqual(len(response.data), 1)

    def test_teacher_sees_all_topics(self):
        self.client.login(email="teacher@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/"
        response = self.client.get(url)

        self.assertEqual(len(response.data), 2)
