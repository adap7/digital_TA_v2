from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User
from courses.models import Course, Exercise, CourseMembership
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

    def test_student_can_see_published(self):
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_student_cannot_see_answer_key(self):
        self.exercise.answer_key = {"correct": "4"}
        self.exercise.save()
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("answer_key", response.data[0])

    def test_teacher_can_create_exercise(self):
        CourseMembership.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseMembership.Role.TEACHER,
        )
        self.client.force_authenticate(self.teacher)
        data = {
            "course": self.course.id,
            "created_by": self.teacher.id,
            "type": "free_text",
            "prompt": "What is 3+3?",
            "order_index": 1,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_teacher_cannot_create_in_unassigned_course(self):
        self.client.force_authenticate(self.teacher)
        data = {
            "course": self.course.id,
            "created_by": self.teacher.id,
            "type": "free_text",
            "prompt": "What is 3+3?",
            "order_index": 1,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_submit_for_review_changes_status(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/courses/exercises/{self.exercise.id}/submit-for-review/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.IN_REVIEW)

    def test_publish_changes_status(self):
        self.exercise.submit_for_review()
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/courses/exercises/{self.exercise.id}/publish/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.PUBLISHED)

    def test_unpublish_changes_status(self):
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/courses/exercises/{self.exercise.id}/unpublish/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.DRAFT)
