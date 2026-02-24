from unittest.mock import patch

from rest_framework.test import APITestCase

from courses.models import Course, CourseMembership, Exercise, Submission, SubmissionMessage
from tenants.models import Tenant
from users.models import User


SUBMIT_URL   = lambda eid: f"/api/v1/exercises/{eid}/submissions/"
DETAIL_URL   = lambda sid: f"/api/v1/submissions/{sid}/"
MESSAGES_URL = lambda sid: f"/api/v1/submissions/{sid}/messages/"

FAKE_AI = "Good attempt! Here's a hint..."


class SubmissionSetupMixin:
    """Common setUp for all submission test cases."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Uni", slug="uni")

        self.admin = User.objects.create_user(
            email="admin@uni.com", password="pass", role="admin", tenant=self.tenant
        )
        self.teacher = User.objects.create_user(
            email="teacher@uni.com", password="pass", role="teacher", tenant=self.tenant
        )
        self.student = User.objects.create_user(
            email="student@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.student2 = User.objects.create_user(
            email="student2@uni.com", password="pass", role="student", tenant=self.tenant
        )

        self.course = Course.objects.create(tenant=self.tenant, title="Math", code="M101")

        CourseMembership.objects.create(
            course=self.course, user=self.teacher, role=CourseMembership.Role.TEACHER
        )
        CourseMembership.objects.create(
            course=self.course, user=self.student, role=CourseMembership.Role.STUDENT
        )
        CourseMembership.objects.create(
            course=self.course, user=self.student2, role=CourseMembership.Role.STUDENT
        )

        self.exercise = Exercise.objects.create(
            course=self.course,
            title="Solve 2+2",
            type=Exercise.Type.FREE_TEXT,
            prompt="What is 2+2?",
            difficulty=1,
            created_by=self.teacher,
        )
        # Publish the exercise so students can submit
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)

        self.mcq_exercise = Exercise.objects.create(
            course=self.course,
            title="Pick one",
            type=Exercise.Type.MCQ,
            prompt="What is 2+2?",
            choices=["3", "4", "5"],
            answer_key={"choice": "4"},
            difficulty=1,
            order_index=1,
            created_by=self.teacher,
        )
        self.mcq_exercise.submit_for_review()
        self.mcq_exercise.publish(self.teacher)


class SubmitAnswerTest(SubmissionSetupMixin, APITestCase):

    @patch("courses.views.evaluate_submission", return_value=FAKE_AI)
    def test_student_can_submit_published_exercise(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "4"}}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("messages", resp.data)
        messages = resp.data["messages"]
        self.assertEqual(len(messages), 2)
        roles = [m["role"] for m in messages]
        self.assertIn("student", roles)
        self.assertIn("assistant", roles)

    def test_student_cannot_submit_draft_exercise(self):
        draft = Exercise.objects.create(
            course=self.course,
            title="Draft Ex",
            type=Exercise.Type.FREE_TEXT,
            prompt="Draft?",
            order_index=2,
            created_by=self.teacher,
        )
        self.client.force_authenticate(self.student)
        resp = self.client.post(SUBMIT_URL(draft.id), {"answer": {"text": "x"}}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_submit_to_unenrolled_course(self):
        other_tenant = Tenant.objects.create(name="Other", slug="other")
        other_student = User.objects.create_user(
            email="s@other.com", password="pass", role="student", tenant=other_tenant
        )
        # other_student has no membership in self.course's tenant — 404 (tenant mismatch)
        self.client.force_authenticate(other_student)
        resp = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "x"}}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_unenrolled_same_tenant_student_gets_403(self):
        unenrolled = User.objects.create_user(
            email="unroll@uni.com", password="pass", role="student", tenant=self.tenant
        )
        self.client.force_authenticate(unenrolled)
        resp = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "x"}}, format="json")
        self.assertEqual(resp.status_code, 403)

    @patch("courses.views.evaluate_submission", return_value=FAKE_AI)
    def test_resubmission_increments_attempt_number(self, _mock):
        self.client.force_authenticate(self.student)
        resp1 = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "4"}}, format="json")
        resp2 = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "four"}}, format="json")
        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        self.assertEqual(resp1.data["attempt_number"], 1)
        self.assertEqual(resp2.data["attempt_number"], 2)

    @patch("courses.views.evaluate_submission", return_value=FAKE_AI)
    def test_mcq_sets_is_correct(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            SUBMIT_URL(self.mcq_exercise.id),
            {"answer": {"choice": "4"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["is_correct"])

    @patch("courses.views.evaluate_submission", return_value=FAKE_AI)
    def test_mcq_wrong_answer_is_not_correct(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            SUBMIT_URL(self.mcq_exercise.id),
            {"answer": {"choice": "3"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data["is_correct"])

    @patch("courses.views.evaluate_submission", side_effect=Exception("API down"))
    def test_llm_failure_returns_503(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(SUBMIT_URL(self.exercise.id), {"answer": {"text": "4"}}, format="json")
        self.assertEqual(resp.status_code, 503)
        # Nothing should have been saved
        self.assertEqual(Submission.objects.count(), 0)


class SubmissionVisibilityTest(SubmissionSetupMixin, APITestCase):

    def _make_submission(self, student):
        sub = Submission.objects.create(
            exercise=self.exercise,
            student=student,
            answer={"text": "4"},
            attempt_number=1,
        )
        SubmissionMessage.objects.create(
            submission=sub, role=SubmissionMessage.Role.STUDENT, content="4"
        )
        SubmissionMessage.objects.create(
            submission=sub, role=SubmissionMessage.Role.ASSISTANT, content=FAKE_AI
        )
        return sub

    def test_student_only_sees_own_submissions(self):
        self._make_submission(self.student)
        self._make_submission(self.student2)
        self.client.force_authenticate(self.student)
        resp = self.client.get(SUBMIT_URL(self.exercise.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["exercise"], self.exercise.id)

    def test_teacher_sees_all_submissions(self):
        self._make_submission(self.student)
        self._make_submission(self.student2)
        self.client.force_authenticate(self.teacher)
        resp = self.client.get(SUBMIT_URL(self.exercise.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)
        # Teacher serializer includes student field
        self.assertIn("student", resp.data[0])

    def test_unassigned_teacher_cannot_list_submissions(self):
        other_teacher = User.objects.create_user(
            email="t2@uni.com", password="pass", role="teacher", tenant=self.tenant
        )
        self._make_submission(self.student)
        self.client.force_authenticate(other_teacher)
        resp = self.client.get(SUBMIT_URL(self.exercise.id))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_any_submission(self):
        sub = self._make_submission(self.student)
        self.client.force_authenticate(self.admin)
        resp = self.client.get(DETAIL_URL(sub.id))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("student", resp.data)

    def test_student_cannot_see_other_students_submission(self):
        sub = self._make_submission(self.student2)
        self.client.force_authenticate(self.student)
        resp = self.client.get(DETAIL_URL(sub.id))
        self.assertEqual(resp.status_code, 404)

    def test_cross_tenant_submission_access_forbidden(self):
        sub = self._make_submission(self.student)
        other_tenant = Tenant.objects.create(name="X", slug="x")
        other_admin = User.objects.create_user(
            email="a@x.com", password="pass", role="admin", tenant=other_tenant
        )
        self.client.force_authenticate(other_admin)
        resp = self.client.get(DETAIL_URL(sub.id))
        self.assertEqual(resp.status_code, 404)


class FollowUpMessageTest(SubmissionSetupMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.submission = Submission.objects.create(
            exercise=self.exercise,
            student=self.student,
            answer={"text": "4"},
            attempt_number=1,
        )
        SubmissionMessage.objects.create(
            submission=self.submission,
            role=SubmissionMessage.Role.STUDENT,
            content="4",
        )
        SubmissionMessage.objects.create(
            submission=self.submission,
            role=SubmissionMessage.Role.ASSISTANT,
            content=FAKE_AI,
        )

    @patch("courses.views.get_followup_response", return_value="Great follow-up!")
    def test_student_can_send_followup(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            MESSAGES_URL(self.submission.id),
            {"content": "Can you give me another hint?"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "assistant")
        self.assertEqual(resp.data["content"], "Great follow-up!")
        # 4 messages total: initial student+AI + new student+AI
        self.assertEqual(self.submission.messages.count(), 4)

    @patch("courses.views.get_followup_response", side_effect=Exception("API down"))
    def test_followup_llm_failure_returns_503(self, _mock):
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            MESSAGES_URL(self.submission.id),
            {"content": "Help?"},
            format="json",
        )
        self.assertEqual(resp.status_code, 503)
        # No new messages saved
        self.assertEqual(self.submission.messages.count(), 2)

    def test_other_student_cannot_send_followup(self):
        self.client.force_authenticate(self.student2)
        resp = self.client.post(
            MESSAGES_URL(self.submission.id),
            {"content": "Sneaky?"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
