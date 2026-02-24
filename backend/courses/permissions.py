from rest_framework.permissions import BasePermission
from users.models import UserRole
from .models import CourseMembership

# ADMIN ONLY
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )

# TEACHER OR ADMIN
class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [UserRole.TEACHER, UserRole.ADMIN]
        )

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin always allowed inside tenant
        if user.role == UserRole.ADMIN:
            return obj.course.tenant == user.tenant

        # Teacher: must belong to course as teacher
        if user.role == UserRole.TEACHER:
            return CourseMembership.objects.filter(
                course=obj.course,
                user=user,
                role=CourseMembership.Role.TEACHER,
            ).exists()

        return False

# STUDENT READ ONLY PUBLISHED
class IsStudentReadOnlyPublished(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role != UserRole.STUDENT:
            return False

        # Must belong to course
        is_enrolled = CourseMembership.objects.filter(
            course=obj.course,
            user=user,
            role=CourseMembership.Role.STUDENT,
        ).exists()

        return is_enrolled and obj.status == obj.Status.PUBLISHED