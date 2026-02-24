from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User
from courses.models import Course, Exercise
from tenants.models import Tenant


class ExerciseVisibilityTest(APITestCase):
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
            code="M101",
        )

        self.exercise = Exercise.objects.create(
            course=self.course,
            title="Test Ex",
            type="free_text",
            prompt="Solve 2+2",
            created_by=self.teacher,
        )

    def test_student_cannot_see_draft(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(len(response.data), 0)
