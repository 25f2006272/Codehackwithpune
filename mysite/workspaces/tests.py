from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta
from django.utils import timezone

from .models import Workspace, WorkspaceMembership, WorkspaceInvitation
from audit.models import AuditLog


User = get_user_model()


class WorkspaceAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPassword123!"
        )

        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="TestPassword123!"
        )

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="TestPassword123!"
        )

        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="TestPassword123!"
        )

        self.client.force_authenticate(user=self.owner)

    def create_workspace(self):

        response = self.client.post(
            "/api/v1/workspaces/",
            {
                "name": "Engineering Workspace",
                "description": "Testing workspace",
                "workspace_type": "HACKATHON",
                "logo_url": ""
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        return Workspace.objects.get(pk=response.data["id"])

    def add_member(self, workspace, user, role):

        return WorkspaceMembership.objects.create(
            workspace=workspace,
            user=user,
            role=role,
            status=WorkspaceMembership.Status.ACTIVE,
            added_by=self.owner
        )

    # 1. Workspace creation and automatic owner assignment

    def test_workspace_creation_creates_owner_membership(self):

        workspace = self.create_workspace()

        membership = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.owner
        )

        self.assertEqual(workspace.owner, self.owner)
        self.assertEqual(membership.role, "OWNER")
        self.assertEqual(membership.status, "ACTIVE")

        self.assertTrue(
            AuditLog.objects.filter(
                workspace=workspace,
                action="WORKSPACE_CREATED"
            ).exists()
        )

    # 2. Users can only see their own workspaces

    def test_user_cannot_see_other_workspaces(self):

        own_workspace = self.create_workspace()

        other_workspace = Workspace.objects.create(
            name="Private Workspace",
            slug="private-workspace-test",
            owner=self.member,
            created_by=self.member
        )

        WorkspaceMembership.objects.create(
            workspace=other_workspace,
            user=self.member,
            role="OWNER",
            status="ACTIVE",
            added_by=self.member
        )

        response = self.client.get("/api/v1/workspaces/")

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            item["id"] for item in response.data
        ]

        self.assertIn(own_workspace.id, returned_ids)
        self.assertNotIn(other_workspace.id, returned_ids)

    # 3. Viewer cannot update workspace

    def test_viewer_cannot_update_workspace(self):

        workspace = self.create_workspace()

        self.add_member(
            workspace,
            self.viewer,
            WorkspaceMembership.Role.VIEWER
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.patch(
            f"/api/v1/workspaces/{workspace.id}/",
            {"name": "Unauthorized Update"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 4. Workspace members can view member list

    def test_member_can_view_workspace_members(self):

        workspace = self.create_workspace()

        self.add_member(
            workspace,
            self.member,
            WorkspaceMembership.Role.MEMBER
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.get(
            f"/api/v1/workspaces/{workspace.id}/members/"
        )

        self.assertEqual(response.status_code, 200)

        usernames = [
            item["username"] for item in response.data
        ]

        self.assertIn("owner", usernames)
        self.assertIn("member", usernames)

    # 5. Owner can invite members

    def test_owner_can_invite_member(self):

        workspace = self.create_workspace()

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.id}/invitations/",
            {
                "email": "newuser@example.com",
                "invited_role": "MEMBER"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        invitation = WorkspaceInvitation.objects.get(
            token=response.data["token"]
        )

        self.assertEqual(invitation.status, "PENDING")

    # 6. Admin cannot invite another Admin

    def test_admin_cannot_invite_another_admin(self):

        workspace = self.create_workspace()

        self.add_member(
            workspace,
            self.admin,
            WorkspaceMembership.Role.ADMIN
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.id}/invitations/",
            {
                "email": "newadmin@example.com",
                "invited_role": "ADMIN"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 7. Invitation acceptance with matching email

    def test_invited_user_can_accept_invitation(self):

        workspace = self.create_workspace()

        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=self.member.email,
            invited_by=self.owner,
            invited_role="MEMBER",
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f"/api/v1/invitations/{invitation.token}/accept/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        invitation.refresh_from_db()

        self.assertEqual(invitation.status, "ACCEPTED")

        membership = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.member
        )

        self.assertEqual(membership.role, "MEMBER")
        self.assertEqual(membership.status, "ACTIVE")

    # 8. Ownership transfer keeps both records synchronized

    def test_ownership_transfer(self):

        workspace = self.create_workspace()

        target = self.add_member(
            workspace,
            self.member,
            WorkspaceMembership.Role.MEMBER
        )

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.id}/transfer-ownership/",
            {"membership_id": target.id},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        workspace.refresh_from_db()

        old_owner = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.owner
        )

        new_owner = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.member
        )

        self.assertEqual(workspace.owner, self.member)
        self.assertEqual(old_owner.role, "ADMIN")
        self.assertEqual(new_owner.role, "OWNER")

    # 9. Owner cannot leave without transferring ownership

    def test_owner_cannot_leave_workspace(self):

        workspace = self.create_workspace()

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.id}/leave/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        membership = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.owner
        )

        self.assertEqual(membership.status, "ACTIVE")

    # 10. Owner can archive workspace

    def test_owner_can_archive_workspace(self):

        workspace = self.create_workspace()

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.id}/archive/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        workspace.refresh_from_db()

        self.assertEqual(
            workspace.status,
            Workspace.Status.ARCHIVED
        )