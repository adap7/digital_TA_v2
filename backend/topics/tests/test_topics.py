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


class TopicCRUDTest(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test3", slug="test3")

        self.admin = User.objects.create_user(
            email="admin3@test.com",
            password="pass",
            role="admin",
            tenant=self.tenant,
        )
        self.teacher = User.objects.create_user(
            email="teacher3@test.com",
            password="pass",
            role="teacher",
            tenant=self.tenant,
        )
        self.teacher_unassigned = User.objects.create_user(
            email="teacher3b@test.com",
            password="pass",
            role="teacher",
            tenant=self.tenant,
        )
        self.student = User.objects.create_user(
            email="student3@test.com",
            password="pass",
            role="student",
            tenant=self.tenant,
        )
        self.student_unenrolled = User.objects.create_user(
            email="student3b@test.com",
            password="pass",
            role="student",
            tenant=self.tenant,
        )

        self.course = Course.objects.create(
            tenant=self.tenant, title="CS", code="CS301"
        )
        CourseMembership.objects.create(user=self.teacher, course=self.course, role="teacher")
        CourseMembership.objects.create(user=self.student, course=self.course, role="student")

        self.published = Topic.objects.create(
            course=self.course, title="Published Topic", order_index=1, is_published=True
        )
        self.draft = Topic.objects.create(
            course=self.course, title="Draft Topic", order_index=2, is_published=False
        )

    def detail_url(self, topic):
        return f"/api/v1/topics/{topic.id}/"

    def list_url(self):
        return f"/api/v1/courses/{self.course.id}/topics/"

    # --- GET detail ---

    def test_enrolled_student_can_get_published_topic(self):
        self.client.login(email="student3@test.com", password="pass")
        self.assertEqual(self.client.get(self.detail_url(self.published)).status_code, 200)

    def test_enrolled_student_cannot_get_draft_topic(self):
        self.client.login(email="student3@test.com", password="pass")
        self.assertEqual(self.client.get(self.detail_url(self.draft)).status_code, 404)

    def test_unenrolled_student_cannot_get_published_topic(self):
        self.client.login(email="student3b@test.com", password="pass")
        self.assertEqual(self.client.get(self.detail_url(self.published)).status_code, 404)

    def test_teacher_can_get_draft_topic(self):
        self.client.login(email="teacher3@test.com", password="pass")
        self.assertEqual(self.client.get(self.detail_url(self.draft)).status_code, 200)

    def test_admin_can_get_any_topic(self):
        self.client.login(email="admin3@test.com", password="pass")
        self.assertEqual(self.client.get(self.detail_url(self.published)).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(self.draft)).status_code, 200)

    # --- PATCH ---

    def test_assigned_teacher_can_patch_topic(self):
        self.client.login(email="teacher3@test.com", password="pass")
        response = self.client.patch(
            self.detail_url(self.published),
            {"title": "Updated"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated")

    def test_unassigned_teacher_cannot_patch_topic(self):
        self.client.login(email="teacher3b@test.com", password="pass")
        response = self.client.patch(
            self.detail_url(self.published),
            {"title": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_patch_topic(self):
        self.client.login(email="student3@test.com", password="pass")
        response = self.client.patch(
            self.detail_url(self.published),
            {"title": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_patch_topic(self):
        self.client.login(email="admin3@test.com", password="pass")
        response = self.client.patch(
            self.detail_url(self.published),
            {"title": "Admin Edit"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    # --- DELETE ---

    def test_assigned_teacher_can_delete_topic(self):
        self.client.login(email="teacher3@test.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(self.draft)).status_code, 204)
        self.assertFalse(Topic.objects.filter(id=self.draft.id).exists())

    def test_unassigned_teacher_cannot_delete_topic(self):
        self.client.login(email="teacher3b@test.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(self.published)).status_code, 403)

    def test_student_cannot_delete_topic(self):
        self.client.login(email="student3@test.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(self.published)).status_code, 403)

    # --- List-level permission ---

    def test_unenrolled_student_gets_empty_list(self):
        self.client.login(email="student3b@test.com", password="pass")
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_unassigned_teacher_cannot_create_topic(self):
        self.client.login(email="teacher3b@test.com", password="pass")
        response = self.client.post(self.list_url(), {"title": "Sneaky", "order_index": 99})
        self.assertEqual(response.status_code, 403)
