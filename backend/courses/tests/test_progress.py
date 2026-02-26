from rest_framework.test import APITestCase

from courses.models import Course, CourseMembership, Exercise, Submission
from tenants.models import Tenant
from users.models import User


PROGRESS_URL = lambda cid, **params: (
    f"/api/v1/courses/{cid}/progress/"
    + (f"?student={params['student']}" if "student" in params else "")
)


class CourseProgressTest(APITestCase):
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
            email="other@uni.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.student = User.objects.create_user(
            email="student@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.student2 = User.objects.create_user(
            email="student2@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.cross_tenant_user = User.objects.create_user(
            email="x@other.com", password="pass", role="teacher", tenant=self.other_tenant
        )

        self.course = Course.objects.create(tenant=self.tenant, title="Math", code="M101")

        CourseMembership.objects.create(course=self.course, user=self.teacher, role="teacher")
        CourseMembership.objects.create(course=self.course, user=self.student, role="student")
        CourseMembership.objects.create(course=self.course, user=self.student2, role="student")

        self.ex1 = Exercise.objects.create(
            course=self.course, title="Q1", type=Exercise.Type.FREE_TEXT,
            prompt="Q1", difficulty=1, created_by=self.teacher,
        )
        self.ex1.submit_for_review()
        self.ex1.publish(self.teacher)

        self.ex2 = Exercise.objects.create(
            course=self.course, title="Q2", type=Exercise.Type.FREE_TEXT,
            prompt="Q2", difficulty=1, order_index=1, created_by=self.teacher,
        )
        self.ex2.submit_for_review()
        self.ex2.publish(self.teacher)

    def _submit(self, exercise, student, attempt, is_correct=None):
        return Submission.objects.create(
            exercise=exercise,
            student=student,
            answer={"text": "ans"},
            attempt_number=attempt,
            is_correct=is_correct,
        )

    # --- Student: own progress ---

    def test_student_gets_own_progress(self):
        self._submit(self.ex1, self.student, 1, is_correct=True)
        self._submit(self.ex2, self.student, 1, is_correct=False)

        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_exercises"], 2)
        self.assertEqual(response.data["attempted"], 2)
        self.assertEqual(response.data["correct"], 1)
        self.assertEqual(response.data["correct_rate"], 0.5)

    def test_only_latest_attempt_counts(self):
        # 3 attempts on ex1; latest (attempt 3) is correct
        self._submit(self.ex1, self.student, 1, is_correct=False)
        self._submit(self.ex1, self.student, 2, is_correct=False)
        self._submit(self.ex1, self.student, 3, is_correct=True)

        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["attempted"], 1)  # one exercise attempted
        self.assertEqual(response.data["correct"], 1)

    def test_teacher_is_correct_overrides_ai_grade(self):
        sub = self._submit(self.ex1, self.student, 1, is_correct=False)
        sub.teacher_is_correct = True
        sub.save()

        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))

        self.assertEqual(response.data["correct"], 1)

    def test_ungraded_counts_as_attempted_not_correct(self):
        self._submit(self.ex1, self.student, 1, is_correct=None)

        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))

        self.assertEqual(response.data["attempted"], 1)
        self.assertEqual(response.data["correct"], 0)

    def test_student_cannot_query_other_student(self):
        self.client.login(email="student@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id, student=self.student2.id))
        self.assertEqual(response.status_code, 403)

    def test_unenrolled_student_gets_403(self):
        unenrolled = User.objects.create_user(
            email="new@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.client.login(email="new@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))
        self.assertEqual(response.status_code, 403)

    # --- Teacher ---

    def test_assigned_teacher_can_query_single_student(self):
        self._submit(self.ex1, self.student, 1, is_correct=True)

        self.client.login(email="teacher@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id, student=self.student.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["student_id"], self.student.id)

    def test_unassigned_teacher_gets_403(self):
        self.client.login(email="other@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))
        self.assertEqual(response.status_code, 403)

    # --- Admin aggregate ---

    def test_admin_gets_aggregate(self):
        self._submit(self.ex1, self.student, 1, is_correct=True)
        self._submit(self.ex1, self.student2, 1, is_correct=False)

        self.client.login(email="admin@uni.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["enrolled_students"], 2)
        self.assertIn("average_correct_rate", response.data)

    # --- Cross-tenant ---

    def test_cross_tenant_gets_404(self):
        self.client.login(email="x@other.com", password="pass")
        response = self.client.get(PROGRESS_URL(self.course.id))
        self.assertEqual(response.status_code, 404)
