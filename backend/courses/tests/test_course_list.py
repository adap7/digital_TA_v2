from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Tenant
from users.models import User, UserRole
from courses.models import Course, CourseMembership


class CourseListTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(
            name="Demo Uni",
            slug="demo-uni",
        )

        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            role=UserRole.ADMIN,
            tenant=self.tenant,
            is_staff=True,
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            password="pass",
            role=UserRole.STUDENT,
            tenant=self.tenant,
        )

        self.course = Course.objects.create(
            tenant=self.tenant,
            title="Calculus I",
            code="CALC1",
        )

        CourseMembership.objects.create(
            user=self.student,
            course=self.course,
            role=CourseMembership.Role.STUDENT,
        )

    def test_admin_sees_courses(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/courses/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_student_sees_assigned_courses(self):
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/v1/courses/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
