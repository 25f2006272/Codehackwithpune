from rest_framework.permissions import BasePermission

from .services import get_project_access


class IsWorkspaceOrProjectMember(BasePermission):

    def has_object_permission(self, request, view, obj):

        try:
            get_project_access(request.user, obj)
            return True

        except Exception:
            return False


class IsProjectManager(BasePermission):

    def has_object_permission(self, request, view, obj):

        try:
            workspace_membership, project_membership = (
                get_project_access(request.user, obj)
            )

            return (
                workspace_membership.role in ["OWNER", "ADMIN"]
                or (
                    project_membership is not None
                    and project_membership.project_role == "LEAD"
                )
            )

        except Exception:
            return False