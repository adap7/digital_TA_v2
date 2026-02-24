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


class TopicParentTest(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test2", slug="test2")

        self.teacher = User.objects.create_user(
            email="teacher2@test.com",
            password="pass",
            role="teacher",
            tenant=self.tenant,
        )

        self.course = Course.objects.create(
            tenant=self.tenant,
            title="Math",
            code="MATH201",
        )

        CourseMembership.objects.create(
            user=self.teacher,
            course=self.course,
            role="teacher",
        )

        self.parent = Topic.objects.create(
            course=self.course,
            title="Unit 1",
            order_index=1,
            is_published=True,
        )

    def test_teacher_can_create_subtopic(self):
        self.client.login(email="teacher2@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/"
        response = self.client.post(url, {
            "title": "Lesson 1",
            "order_index": 1,
            "parent": self.parent.id,
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parent"], self.parent.id)

    def test_filter_by_parent_null_returns_top_level(self):
        Topic.objects.create(
            course=self.course,
            title="Lesson 1",
            order_index=1,
            parent=self.parent,
            is_published=True,
        )
        self.client.login(email="teacher2@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/?parent=null"
        response = self.client.get(url)

        titles = [t["title"] for t in response.data]
        self.assertIn("Unit 1", titles)
        self.assertNotIn("Lesson 1", titles)

    def test_filter_by_parent_id_returns_subtopics(self):
        child = Topic.objects.create(
            course=self.course,
            title="Lesson 1",
            order_index=1,
            parent=self.parent,
            is_published=True,
        )
        self.client.login(email="teacher2@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/?parent={self.parent.id}"
        response = self.client.get(url)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], child.id)

    def test_cross_course_parent_rejected(self):
        other_course = Course.objects.create(
            tenant=self.tenant,
            title="Physics",
            code="PHY201",
        )
        other_parent = Topic.objects.create(
            course=other_course,
            title="Other Unit",
            order_index=1,
        )
        self.client.login(email="teacher2@test.com", password="pass")
        url = f"/api/v1/courses/{self.course.id}/topics/"
        response = self.client.post(url, {
            "title": "Bad Child",
            "order_index": 1,
            "parent": other_parent.id,
        })

        self.assertEqual(response.status_code, 400)
