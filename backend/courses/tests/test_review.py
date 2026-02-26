from rest_framework.test import APITestCase

from courses.models import Course, CourseMembership, Exercise, Submission
from tenants.models import Tenant
from users.models import User


REVIEW_URL = lambda sid: f"/api/v1/submissions/{sid}/review/"
DETAIL_URL  = lambda sid: f"/api/v1/submissions/{sid}/"


class SubmissionReviewTest(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Uni", slug="uni")
        self.other_tenant = Tenant.objects.create(name="Other", slug="other")

        self.admin = User.objects.create_user(
            email="admin@uni.com", password="pass", role="admin", tenant=self.tenant
        )
        self.teacher = User.objects.create_user(
            email="teacher@uni.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.teacher_unassigned = User.objects.create_user(
            email="other_teacher@uni.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.student = User.objects.create_user(
            email="student@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.cross_tenant_teacher = User.objects.create_user(
            email="teacher@other.com", password="pass", role="teacher", tenant=self.other_tenant
        )

        self.course = Course.objects.create(tenant=self.tenant, title="Math", code="M101")

        CourseMembership.objects.create(
            course=self.course, user=self.teacher, role=CourseMembership.Role.TEACHER
        )
        CourseMembership.objects.create(
            course=self.course, user=self.student, role=CourseMembership.Role.STUDENT
        )

        self.exercise = Exercise.objects.create(
            course=self.course,
            title="Solve 2+2",
            type=Exercise.Type.FREE_TEXT,
            prompt="What is 2+2?",
            difficulty=1,
            created_by=self.teacher,
        )
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)

        self.submission = Submission.objects.create(
            exercise=self.exercise,
            student=self.student,
            answer={"text": "4"},
            attempt_number=1,
            is_correct=None,
        )

    # --- Assigned teacher ---

    def test_assigned_teacher_can_review(self):
        self.client.login(email="teacher@uni.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Good try!", "teacher_is_correct": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["teacher_comment"], "Good try!")
        self.assertTrue(response.data["teacher_is_correct"])

    def test_review_sets_reviewed_by_and_reviewed_at(self):
        self.client.login(email="teacher@uni.com", password="pass")
        self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Nice work.", "teacher_is_correct": True},
        )
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.reviewed_by, self.teacher)
        self.assertIsNotNone(self.submission.reviewed_at)

    def test_partial_review_comment_only(self):
        self.client.login(email="teacher@uni.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Look at your signs."},
        )
        self.assertEqual(response.status_code, 200)
        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.teacher_is_correct)
        self.assertEqual(self.submission.teacher_comment, "Look at your signs.")

    def test_rereview_overwrites_previous(self):
        self.client.login(email="teacher@uni.com", password="pass")
        self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "First review", "teacher_is_correct": False},
        )
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Updated review", "teacher_is_correct": True},
        )
        self.assertEqual(response.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.teacher_comment, "Updated review")
        self.assertTrue(self.submission.teacher_is_correct)

    # --- Admin ---

    def test_admin_can_review_any_submission_in_tenant(self):
        self.client.login(email="admin@uni.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Admin says great!", "teacher_is_correct": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reviewed_by"], self.admin.id)

    # --- Blocked roles ---

    def test_student_cannot_review(self):
        self.client.login(email="student@uni.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "I reviewed myself"},
        )
        self.assertEqual(response.status_code, 403)

    def test_unassigned_teacher_cannot_review(self):
        self.client.login(email="other_teacher@uni.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Sneaky review"},
        )
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_returns_404(self):
        self.client.login(email="teacher@other.com", password="pass")
        response = self.client.patch(
            REVIEW_URL(self.submission.id),
            {"teacher_comment": "Cross-tenant review"},
        )
        self.assertEqual(response.status_code, 404)

    # --- Student visibility ---

    def test_student_sees_teacher_comment_in_detail(self):
        self.submission.teacher_comment = "Well done!"
        self.submission.teacher_is_correct = True
        self.submission.reviewed_by = self.teacher
        self.submission.save()

        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(DETAIL_URL(self.submission.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["teacher_comment"], "Well done!")
        self.assertTrue(response.data["teacher_is_correct"])
        # reviewed_by must NOT be exposed to students
        self.assertNotIn("reviewed_by", response.data)
