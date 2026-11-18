from rest_framework.permissions import BasePermission
from .models import UserRole

class IsAdmin(BasePermission):
    """Allows access only to Admin users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_user)

class IsReviewer(BasePermission):
    """Allows access only to authorized Reviewers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_reviewer)

class IsClaimant(BasePermission):
    """Allows access only to Claimants."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_claimant)

class IsReviewerOrAdmin(BasePermission):
    """Allows access to Reviewers and Admins."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_reviewer or request.user.is_admin_user)
        )

