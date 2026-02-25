from rest_framework.test import APITestCase

from tenants.models import Tenant
from users.models import User
from courses.models import Course, CourseMembership


class CourseMembershipTest(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="TestOrg", slug="testorg")
        self.other_tenant = Tenant.objects.create(name="Other", slug="other")

        self.admin = User.objects.create_user(
            email="admin@m.com", password="pass", role="admin", tenant=self.tenant
        )
        self.super_teacher = User.objects.create_user(
            email="super@m.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.teacher_regular = User.objects.create_user(
            email="teacher@m.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.teacher_other = User.objects.create_user(
            email="teacherx@m.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.student = User.objects.create_user(
            email="student@m.com", password="pass", role="student", tenant=self.tenant
        )
        self.student2 = User.objects.create_user(
            email="student2@m.com", password="pass", role="student", tenant=self.tenant
        )
        self.cross_tenant_user = User.objects.create_user(
            email="cross@m.com", password="pass", role="student", tenant=self.other_tenant
        )

        self.course = Course.objects.create(tenant=self.tenant, title="CS101", code="CS101")

        # super_teacher assigned with is_super_teacher=True
        CourseMembership.objects.create(
            user=self.super_teacher,
            course=self.course,
            role="teacher",
            is_super_teacher=True,
        )
        # regular teacher assigned
        CourseMembership.objects.create(
            user=self.teacher_regular,
            course=self.course,
            role="teacher",
            is_super_teacher=False,
        )
        # student enrolled
        CourseMembership.objects.create(
            user=self.student,
            course=self.course,
            role="student",
        )

    def list_url(self):
        return f"/api/v1/courses/{self.course.id}/members/"

    def detail_url(self, pk):
        return f"/api/v1/courses/{self.course.id}/members/{pk}/"

    # --- GET list ---

    def test_admin_can_list_members(self):
        self.client.login(email="admin@m.com", password="pass")
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)  # super_teacher + teacher + student

    def test_super_teacher_can_list_members(self):
        self.client.login(email="super@m.com", password="pass")
        self.assertEqual(self.client.get(self.list_url()).status_code, 200)

    def test_regular_teacher_can_list_members(self):
        self.client.login(email="teacher@m.com", password="pass")
        self.assertEqual(self.client.get(self.list_url()).status_code, 200)

    def test_unassigned_teacher_cannot_list_members(self):
        self.client.login(email="teacherx@m.com", password="pass")
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    def test_student_cannot_list_members(self):
        self.client.login(email="student@m.com", password="pass")
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    # --- POST (add member) ---

    def test_admin_can_add_student(self):
        self.client.login(email="admin@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.student2.id, "role": "student"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_super_teacher"])

    def test_super_teacher_can_add_student(self):
        self.client.login(email="super@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.student2.id, "role": "student"},
        )
        self.assertEqual(response.status_code, 201)

    def test_super_teacher_can_add_teacher(self):
        self.client.login(email="super@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.teacher_other.id, "role": "teacher"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_super_teacher"])

    def test_regular_teacher_cannot_add_member(self):
        self.client.login(email="teacher@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.student2.id, "role": "student"},
        )
        self.assertEqual(response.status_code, 403)

    def test_super_teacher_cannot_set_is_super_teacher(self):
        self.client.login(email="super@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.teacher_other.id, "role": "teacher", "is_super_teacher": True},
        )
        # Either rejected (403) or silently ignored (201 with is_super_teacher=False)
        if response.status_code == 201:
            self.assertFalse(response.data["is_super_teacher"])
        else:
            self.assertEqual(response.status_code, 403)

    def test_cross_tenant_user_add_rejected(self):
        self.client.login(email="admin@m.com", password="pass")
        response = self.client.post(
            self.list_url(),
            {"user": self.cross_tenant_user.id, "role": "student"},
        )
        self.assertEqual(response.status_code, 400)

    # --- DELETE (remove member) ---

    def test_admin_can_remove_student(self):
        membership = CourseMembership.objects.get(user=self.student, course=self.course)
        self.client.login(email="admin@m.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(membership.id)).status_code, 204)
        self.assertFalse(CourseMembership.objects.filter(id=membership.id).exists())

    def test_super_teacher_can_remove_student(self):
        membership = CourseMembership.objects.get(user=self.student, course=self.course)
        self.client.login(email="super@m.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(membership.id)).status_code, 204)

    def test_super_teacher_cannot_remove_teacher(self):
        membership = CourseMembership.objects.get(
            user=self.teacher_regular, course=self.course
        )
        self.client.login(email="super@m.com", password="pass")
        self.assertEqual(self.client.delete(self.detail_url(membership.id)).status_code, 403)
