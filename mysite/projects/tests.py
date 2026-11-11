from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from workspaces.models import Workspace, WorkspaceMembership

from .models import (
    Project,
    ProjectMembership,
    ProjectActivity,
    ProjectTask,
    ProjectDecision,
    
)

from audit.models import AuditLog


User = get_user_model()


class ProjectAPITests(APITestCase):

    def setUp(self):

        self.owner = User.objects.create_user(
            username="project_owner",
            email="owner@example.com",
            password="TestPassword123!"
        )

        self.admin = User.objects.create_user(
            username="workspace_admin",
            email="admin@example.com",
            password="TestPassword123!"
        )

        self.member = User.objects.create_user(
            username="project_member",
            email="member@example.com",
            password="TestPassword123!"
        )

        self.viewer = User.objects.create_user(
            username="project_viewer",
            email="viewer@example.com",
            password="TestPassword123!"
        )

        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPassword123!"
        )

        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            slug="test-project-workspace",
            owner=self.owner,
            created_by=self.owner
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="OWNER",
            status="ACTIVE"
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.admin,
            role="ADMIN",
            status="ACTIVE"
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="MEMBER",
            status="ACTIVE"
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.viewer,
            role="VIEWER",
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.owner)

    def create_project(self):

        response = self.client.post(
            "/api/v1/projects/",
            {
                "workspace_id": self.workspace.id,
                "name": "Test Project",
                "description": "Testing project management",
                "start_date": "2026-11-10",
                "target_end_date": "2027-01-10"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        return Project.objects.get(id=response.data["id"])

    def add_project_member(self, project, user, role="MEMBER"):

        return ProjectMembership.objects.create(
            project=project,
            user=user,
            project_role=role,
            status="ACTIVE",
            added_by=self.owner
        )

    # 1. Project creation and automatic lead assignment

    def test_project_creation_assigns_creator_as_lead(self):

        project = self.create_project()

        membership = ProjectMembership.objects.get(
            project=project,
            user=self.owner
        )

        self.assertEqual(project.created_by, self.owner)
        self.assertEqual(membership.project_role, "LEAD")
        self.assertEqual(membership.status, "ACTIVE")

        self.assertTrue(
            ProjectActivity.objects.filter(
                project=project,
                activity_type="PROJECT_CREATED"
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                workspace=self.workspace,
                action="PROJECT_CREATED",
                object_id=str(project.id)
            ).exists()
        )

    # 2. Workspace admin can create projects

    def test_workspace_admin_can_create_project(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/projects/",
            {
                "workspace_id": self.workspace.id,
                "name": "Admin Project"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    # 3. Ordinary workspace member cannot create projects

    def test_workspace_member_cannot_create_project(self):

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/v1/projects/",
            {
                "workspace_id": self.workspace.id,
                "name": "Unauthorized Project"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 4. Unassigned workspace member cannot see project

    def test_unassigned_member_cannot_see_project(self):

        project = self.create_project()

        self.client.force_authenticate(user=self.member)

        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

        detail_response = self.client.get(
            f"/api/v1/projects/{project.id}/"
        )

        self.assertEqual(detail_response.status_code, 404)

    # 5. Assigned project member can see project

    def test_assigned_member_can_see_project(self):

        project = self.create_project()

        self.add_project_member(
            project,
            self.member
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)

        project_ids = [
            item["id"] for item in response.data
        ]

        self.assertIn(project.id, project_ids)

    # 6. Owner can add workspace member to project

    def test_owner_can_add_project_member(self):

        project = self.create_project()

        response = self.client.post(
            f"/api/v1/projects/{project.id}/members/",
            {
                "user_id": self.member.id,
                "project_role": "MEMBER"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        self.assertTrue(
            ProjectMembership.objects.filter(
                project=project,
                user=self.member,
                project_role="MEMBER",
                status="ACTIVE"
            ).exists()
        )

    # 7. Non-workspace member cannot join project directly

    def test_non_workspace_member_cannot_be_added(self):

        project = self.create_project()

        response = self.client.post(
            f"/api/v1/projects/{project.id}/members/",
            {
                "user_id": self.outsider.id,
                "project_role": "MEMBER"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # 8. Workspace viewer cannot become project member

    def test_workspace_viewer_cannot_become_project_member(self):

        project = self.create_project()

        response = self.client.post(
            f"/api/v1/projects/{project.id}/members/",
            {
                "user_id": self.viewer.id,
                "project_role": "MEMBER"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # 9. Project viewer cannot update project

    def test_project_viewer_cannot_update_project(self):

        project = self.create_project()

        self.add_project_member(
            project,
            self.member,
            "VIEWER"
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/v1/projects/{project.id}/",
            {"name": "Unauthorized Update"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 10. Owner can transfer project leadership

    def test_owner_can_transfer_project_lead(self):

        project = self.create_project()

        target = self.add_project_member(
            project,
            self.member
        )

        response = self.client.post(
            f"/api/v1/projects/{project.id}/set-lead/",
            {"membership_id": target.id},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        old_lead = ProjectMembership.objects.get(
            project=project,
            user=self.owner
        )

        new_lead = ProjectMembership.objects.get(
            project=project,
            user=self.member
        )

        self.assertEqual(old_lead.project_role, "MEMBER")
        self.assertEqual(new_lead.project_role, "LEAD")

    # 11. Current project lead cannot be removed

    def test_project_lead_cannot_be_removed(self):

        project = self.create_project()

        target = self.add_project_member(
            project,
            self.member
        )

        self.client.post(
            f"/api/v1/projects/{project.id}/set-lead/",
            {"membership_id": target.id},
            format="json"
        )

        response = self.client.delete(
            f"/api/v1/projects/{project.id}/members/{target.id}/"
        )

        self.assertEqual(response.status_code, 400)

        target.refresh_from_db()

        self.assertEqual(target.status, "ACTIVE")

    # 12. Owner can archive project

    def test_owner_can_archive_project(self):

        project = self.create_project()

        response = self.client.post(
            f"/api/v1/projects/{project.id}/archive/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        project.refresh_from_db()

        self.assertEqual(
            project.status,
            Project.Status.ARCHIVED
        )

    # 13. Archived project cannot be updated

    def test_archived_project_cannot_be_updated(self):

        project = self.create_project()

        self.client.post(
            f"/api/v1/projects/{project.id}/archive/",
            {},
            format="json"
        )

        response = self.client.patch(
            f"/api/v1/projects/{project.id}/",
            {"name": "Updated Archived Project"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)
        

class ProjectTaskAPITests(APITestCase):

    def setUp(self):

        self.owner = User.objects.create_user(
            username="task_owner",
            email="taskowner@example.com",
            password="TestPassword123!"
        )

        self.member = User.objects.create_user(
            username="task_member",
            email="taskmember@example.com",
            password="TestPassword123!"
        )

        self.viewer = User.objects.create_user(
            username="task_viewer",
            email="taskviewer@example.com",
            password="TestPassword123!"
        )

        self.outsider = User.objects.create_user(
            username="task_outsider",
            email="outsider@example.com",
            password="TestPassword123!"
        )

        self.workspace = Workspace.objects.create(
            name="Task Testing Workspace",
            slug="task-testing-workspace",
            owner=self.owner,
            created_by=self.owner
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="OWNER",
            status="ACTIVE"
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="MEMBER",
            status="ACTIVE"
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.viewer,
            role="MEMBER",
            status="ACTIVE"
        )

        self.project = Project.objects.create(
            workspace=self.workspace,
            name="Task Testing Project",
            slug="task-testing-project",
            created_by=self.owner
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.owner,
            project_role="LEAD",
            status="ACTIVE"
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
            project_role="MEMBER",
            status="ACTIVE"
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.viewer,
            project_role="VIEWER",
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.owner)

        self.task_url = (
            f"/api/v1/projects/{self.project.id}/tasks/"
        )

    def create_task(self, assigned_to_id=None):

        response = self.client.post(
            self.task_url,
            {
                "title": "Test Backend Task",
                "description": "Testing task functionality.",
                "assigned_to_id": assigned_to_id,
                "priority": "HIGH",
                "due_date": "2026-12-20"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        return ProjectTask.objects.get(
            id=response.data["id"]
        )

    # 1. Owner can create a task

    def test_owner_can_create_task(self):

        task = self.create_task()

        self.assertEqual(task.created_by, self.owner)
        self.assertEqual(task.status, "TODO")
        self.assertEqual(task.priority, "HIGH")

        self.assertTrue(
            ProjectActivity.objects.filter(
                project=self.project,
                activity_type="TASK_CREATED"
            ).exists()
        )

    # 2. Task can be assigned to an active project member

    def test_owner_can_assign_task_to_project_member(self):

        task = self.create_task(
            assigned_to_id=self.member.id
        )

        self.assertEqual(task.assigned_to, self.member)

    # 3. Task cannot be assigned to an outsider

    def test_task_cannot_be_assigned_to_outsider(self):

        response = self.client.post(
            self.task_url,
            {
                "title": "Unauthorized Assignment",
                "assigned_to_id": self.outsider.id,
                "priority": "HIGH"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # 4. Task cannot be assigned to a project viewer

    def test_task_cannot_be_assigned_to_project_viewer(self):

        response = self.client.post(
            self.task_url,
            {
                "title": "Viewer Assignment",
                "assigned_to_id": self.viewer.id,
                "priority": "HIGH"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # 5. Project member cannot create tasks

    def test_project_member_cannot_create_task(self):

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.task_url,
            {
                "title": "Unauthorized Task"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 6. Assigned member can update task status

    def test_assigned_member_can_update_task_status(self):

        task = self.create_task(
            assigned_to_id=self.member.id
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"status": "DONE"},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            200,
            response.data
        )

        task.refresh_from_db()

        self.assertEqual(task.status, "DONE")
        self.assertIsNotNone(task.completed_at)

    # 7. Assigned member cannot change task title

    def test_assigned_member_cannot_change_task_title(self):

        task = self.create_task(
            assigned_to_id=self.member.id
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"title": "Unauthorized Title Change"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

        task.refresh_from_db()

        self.assertEqual(
            task.title,
            "Test Backend Task"
        )

    # 8. Member cannot update another person's task

    def test_member_cannot_update_unassigned_task(self):

        task = self.create_task()

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"status": "DONE"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 9. Project viewer cannot update tasks

    def test_project_viewer_cannot_update_task(self):

        task = self.create_task()

        self.client.force_authenticate(user=self.viewer)

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"status": "DONE"},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 10. Reopening a completed task clears completed_at

    def test_reopening_task_clears_completed_at(self):

        task = self.create_task()

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"status": "DONE"},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        task.refresh_from_db()

        self.assertIsNotNone(task.completed_at)

        response = self.client.patch(
            f"{self.task_url}{task.id}/",
            {"status": "IN_PROGRESS"},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        task.refresh_from_db()

        self.assertEqual(task.status, "IN_PROGRESS")
        self.assertIsNone(task.completed_at)

    # 11. Project member can list project tasks

    def test_project_member_can_view_tasks(self):

        self.create_task()

        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.task_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        
class ProjectDecisionAPITests(APITestCase):

    def setUp(self):

        self.owner = User.objects.create_user(
            username="decision_owner",
            email="decisionowner@example.com",
            password="TestPassword123!"
        )

        self.member = User.objects.create_user(
            username="decision_member",
            email="decisionmember@example.com",
            password="TestPassword123!"
        )

        self.other_member = User.objects.create_user(
            username="other_member",
            email="othermember@example.com",
            password="TestPassword123!"
        )

        self.viewer = User.objects.create_user(
            username="decision_viewer",
            email="decisionviewer@example.com",
            password="TestPassword123!"
        )

        self.workspace = Workspace.objects.create(
            name="Decision Testing Workspace",
            slug="decision-testing-workspace",
            owner=self.owner,
            created_by=self.owner
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="OWNER",
            status="ACTIVE"
        )

        for user in [
            self.member,
            self.other_member,
            self.viewer
        ]:
            WorkspaceMembership.objects.create(
                workspace=self.workspace,
                user=user,
                role="MEMBER",
                status="ACTIVE"
            )

        self.project = Project.objects.create(
            workspace=self.workspace,
            name="Decision Testing Project",
            slug="decision-testing-project",
            created_by=self.owner
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.owner,
            project_role="LEAD",
            status="ACTIVE"
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
            project_role="MEMBER",
            status="ACTIVE"
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.other_member,
            project_role="MEMBER",
            status="ACTIVE"
        )

        ProjectMembership.objects.create(
            project=self.project,
            user=self.viewer,
            project_role="VIEWER",
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.owner)

        self.decision_url = (
            f"/api/v1/projects/{self.project.id}/decisions/"
        )

    def create_decision(self, user=None, title="Test Technical Decision"):

        if user is None:
            user = self.owner

        self.client.force_authenticate(user=user)

        response = self.client.post(
            self.decision_url,
            {
                "title": title,
                "context": "Testing project decision management.",
                "decision": "Use Django REST Framework.",
                "rationale": "It provides structured REST APIs.",
                "decision_type": "TECHNICAL"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        return ProjectDecision.objects.get(
            id=response.data["id"]
        )

    def transition_decision(self, decision, new_status):

        return self.client.post(
            f"{self.decision_url}{decision.id}/transition/",
            {"status": new_status},
            format="json"
        )

    # 1. Project lead can create a decision

    def test_project_lead_can_create_decision(self):

        decision = self.create_decision()

        self.assertEqual(
            decision.status,
            ProjectDecision.DecisionStatus.PROPOSED
        )

        self.assertIsNone(decision.decision_date)

    # 2. Project member can propose a decision

    def test_project_member_can_propose_decision(self):

        decision = self.create_decision(
            user=self.member
        )

        self.assertEqual(decision.created_by, self.member)
        self.assertEqual(decision.status, "PROPOSED")

    # 3. Project viewer cannot create a decision

    def test_project_viewer_cannot_create_decision(self):

        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.decision_url,
            {
                "title": "Unauthorized Decision",
                "decision": "Some decision",
                "decision_type": "TECHNICAL"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    # 4. Creator can update their own proposed decision

    def test_creator_can_update_own_proposed_decision(self):

        decision = self.create_decision(
            user=self.member
        )

        response = self.client.patch(
            f"{self.decision_url}{decision.id}/",
            {
                "title": "Updated Decision Title"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        decision.refresh_from_db()

        self.assertEqual(
            decision.title,
            "Updated Decision Title"
        )

    # 5. Member cannot update another member's decision

    def test_member_cannot_update_another_members_decision(self):

        decision = self.create_decision(
            user=self.other_member
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"{self.decision_url}{decision.id}/",
            {
                "title": "Unauthorized Decision Update"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 403)

        decision.refresh_from_db()

        self.assertEqual(
            decision.title,
            "Test Technical Decision"
        )

    # 6. Project lead can accept a proposed decision

    def test_project_lead_can_accept_decision(self):

        decision = self.create_decision()

        response = self.transition_decision(
            decision,
            "ACCEPTED"
        )

        self.assertEqual(
            response.status_code,
            200,
            response.data
        )

        decision.refresh_from_db()

        self.assertEqual(decision.status, "ACCEPTED")
        self.assertIsNotNone(decision.decision_date)

    # 7. Project lead can reject a proposed decision

    def test_project_lead_can_reject_decision(self):

        decision = self.create_decision()

        response = self.transition_decision(
            decision,
            "REJECTED"
        )

        self.assertEqual(response.status_code, 200)

        decision.refresh_from_db()

        self.assertEqual(decision.status, "REJECTED")
        self.assertIsNotNone(decision.decision_date)

    # 8. Project member cannot approve a decision

    def test_project_member_cannot_approve_decision(self):

        decision = self.create_decision()

        self.client.force_authenticate(user=self.member)

        response = self.transition_decision(
            decision,
            "ACCEPTED"
        )

        self.assertEqual(response.status_code, 403)

        decision.refresh_from_db()

        self.assertEqual(decision.status, "PROPOSED")

    # 9. Accepted decision can be superseded

    def test_accepted_decision_can_be_superseded(self):

        decision = self.create_decision()

        accept_response = self.transition_decision(
            decision,
            "ACCEPTED"
        )

        self.assertEqual(accept_response.status_code, 200)

        supersede_response = self.transition_decision(
            decision,
            "SUPERSEDED"
        )

        self.assertEqual(supersede_response.status_code, 200)

        decision.refresh_from_db()

        self.assertEqual(decision.status, "SUPERSEDED")

    # 10. Rejected decision cannot be accepted

    def test_rejected_decision_cannot_be_accepted(self):

        decision = self.create_decision()

        self.transition_decision(decision, "REJECTED")

        response = self.transition_decision(
            decision,
            "ACCEPTED"
        )

        self.assertEqual(response.status_code, 400)

        decision.refresh_from_db()

        self.assertEqual(decision.status, "REJECTED")

    # 11. Accepted decision cannot be directly edited

    def test_accepted_decision_cannot_be_edited(self):

        decision = self.create_decision()

        self.transition_decision(decision, "ACCEPTED")

        response = self.client.patch(
            f"{self.decision_url}{decision.id}/",
            {
                "title": "Modified Accepted Decision"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        decision.refresh_from_db()

        self.assertEqual(
            decision.title,
            "Test Technical Decision"
        )

    # 12. Decision creation generates activity and audit logs

    def test_decision_creation_generates_activity_and_audit(self):

        decision = self.create_decision()

        activity_exists = ProjectActivity.objects.filter(
            project=self.project,
            activity_type="DECISION_RECORDED"
        ).exists()

        audit_exists = AuditLog.objects.filter(
            workspace=self.workspace,
            object_type="ProjectDecision",
            object_id=str(decision.id),
            action="OTHER"
        ).exists()

        self.assertTrue(activity_exists)
        self.assertTrue(audit_exists)