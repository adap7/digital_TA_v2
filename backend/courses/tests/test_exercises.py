from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User
from courses.models import Course, Exercise, CourseMembership
from tenants.models import Tenant
from topics.models import Topic


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
        CourseMembership.objects.create(
            course=self.course,
            user=self.student,
            role=CourseMembership.Role.STUDENT,
        )
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_student_cannot_see_answer_key(self):
        CourseMembership.objects.create(
            course=self.course,
            user=self.student,
            role=CourseMembership.Role.STUDENT,
        )
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
        CourseMembership.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseMembership.Role.TEACHER,
        )
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/exercises/{self.exercise.id}/submit-for-review/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.IN_REVIEW)

    def test_publish_changes_status(self):
        CourseMembership.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseMembership.Role.TEACHER,
        )
        self.exercise.submit_for_review()
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/exercises/{self.exercise.id}/publish/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.PUBLISHED)

    def test_unpublish_changes_status(self):
        CourseMembership.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseMembership.Role.TEACHER,
        )
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/exercises/{self.exercise.id}/unpublish/"
        )
        self.assertEqual(response.status_code, 200)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.status, Exercise.Status.DRAFT)

    def test_exercise_can_be_assigned_topic_in_same_course(self):
        topic = Topic.objects.create(course=self.course, title="Algebra")
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
            "prompt": "Solve for x.",
            "order_index": 1,
            "topic": topic.id,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_exercise_cannot_be_assigned_topic_from_different_course(self):
        other_course = Course.objects.create(
            tenant=self.tenant, title="Physics", code="P101"
        )
        topic = Topic.objects.create(course=other_course, title="Mechanics")
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
            "prompt": "Solve for x.",
            "order_index": 1,
            "topic": topic.id,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_student_cannot_create_exercise(self):
        self.client.force_authenticate(self.student)
        data = {
            "course": self.course.id,
            "created_by": self.student.id,
            "type": "free_text",
            "prompt": "A question.",
            "order_index": 1,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_update_exercise(self):
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        CourseMembership.objects.create(
            course=self.course,
            user=self.student,
            role=CourseMembership.Role.STUDENT,
        )
        self.client.force_authenticate(self.student)
        response = self.client.patch(
            f"/api/v1/exercises/{self.exercise.id}/",
            {"prompt": "Changed."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_submit_for_review(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            f"/api/v1/exercises/{self.exercise.id}/submit-for-review/"
        )
        self.assertEqual(response.status_code, 403)

    def test_unenrolled_student_cannot_see_exercises(self):
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(self.student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_admin_can_create_exercise_without_membership(self):
        admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            role="admin",
            tenant=self.tenant,
        )
        self.client.force_authenticate(admin)
        data = {
            "course": self.course.id,
            "created_by": admin.id,
            "type": "free_text",
            "prompt": "Admin question.",
            "order_index": 1,
        }
        response = self.client.post(
            f"/api/v1/courses/{self.course.id}/exercises/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_admin_can_see_draft_exercises(self):
        admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            role="admin",
            tenant=self.tenant,
        )
        self.client.force_authenticate(admin)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_teacher_cannot_update_exercise_in_unassigned_course(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.patch(
            f"/api/v1/exercises/{self.exercise.id}/",
            {"prompt": "Changed."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_submit_review_in_unassigned_course(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            f"/api/v1/exercises/{self.exercise.id}/submit-for-review/"
        )
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_exercise_access_forbidden(self):
        other_tenant = Tenant.objects.create(name="Other", slug="other")
        other_student = User.objects.create_user(
            email="other@other.com",
            password="pass",
            role="student",
            tenant=other_tenant,
        )
        self.exercise.submit_for_review()
        self.exercise.publish(self.teacher)
        self.client.force_authenticate(other_student)
        response = self.client.get(
            f"/api/v1/courses/{self.course.id}/exercises/"
        )
        self.assertEqual(response.status_code, 404)
