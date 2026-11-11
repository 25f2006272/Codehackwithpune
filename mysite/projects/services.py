import uuid

from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound
)

from workspaces.models import (
    Workspace,
    WorkspaceMembership
)

from workspaces.services import (
    get_membership,
    require_manager,
    ensure_workspace_active,
    record_audit
)

from .models import (
    Project,
    ProjectMembership,
    ProjectActivity,
    ProjectTask,
    ProjectDecision,
    
)

from django.contrib.auth import get_user_model

User = get_user_model()


def get_project_access(user, project):

    workspace_membership = get_membership(
        user,
        project.workspace
    )

    project_membership = ProjectMembership.objects.filter(
        project=project,
        user=user,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if project.workspace.status == Workspace.Status.SUSPENDED:
        raise PermissionDenied("Workspace access is suspended.")

    allowed_workspace_roles = [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN,
        WorkspaceMembership.Role.VIEWER
    ]

    if workspace_membership.role in allowed_workspace_roles:
        return workspace_membership, project_membership

    if not project_membership:
        raise PermissionDenied(
            "You are not a member of this project."
        )

    return workspace_membership, project_membership


def require_project_manager(user, project):

    workspace_membership, project_membership = get_project_access(
        user,
        project
    )

    is_workspace_manager = workspace_membership.role in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN
    ]

    is_project_lead = (
        project_membership is not None
        and project_membership.project_role == ProjectMembership.Role.LEAD
    )

    if not is_workspace_manager and not is_project_lead:
        raise PermissionDenied(
            "Only workspace managers or project leads can perform this action."
        )

    ensure_workspace_active(project.workspace)

    if project.status == Project.Status.ARCHIVED:
        raise ValidationError("Archived projects cannot be modified.")

    return workspace_membership, project_membership


def create_project_activity(
    project,
    actor,
    activity_type,
    description,
    metadata=None
):

    return ProjectActivity.objects.create(
        project=project,
        actor=actor,
        activity_type=activity_type,
        description=description,
        metadata=metadata or {}
    )


# -------------------------------------------------
# CREATE PROJECT
# -------------------------------------------------

@transaction.atomic
def create_project(actor, workspace_id, validated_data, request=None):

    workspace = Workspace.objects.select_for_update().filter(
        pk=workspace_id
    ).first()

    if not workspace:
        raise NotFound("Workspace not found.")

    require_manager(actor, workspace)
    ensure_workspace_active(workspace)

    name = validated_data["name"].strip()

    base_slug = slugify(name)[:200] or "project"

    slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

    project = Project.objects.create(
        workspace=workspace,
        name=name,
        slug=slug,
        description=validated_data.get("description", ""),
        start_date=validated_data.get("start_date"),
        target_end_date=validated_data.get("target_end_date"),
        created_by=actor
    )

    ProjectMembership.objects.create(
        project=project,
        user=actor,
        project_role=ProjectMembership.Role.LEAD,
        status=ProjectMembership.Status.ACTIVE,
        added_by=actor
    )

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.PROJECT_CREATED,
        f"{actor.username} created project {project.name}."
    )

    record_audit(
        actor,
        workspace,
        "PROJECT_CREATED",
        f"{actor.username} created project {project.name}.",
        object_type="Project",
        object_id=project.id,
        request=request
    )

    return project


# -------------------------------------------------
# UPDATE PROJECT
# -------------------------------------------------

@transaction.atomic
def update_project(actor, project, data, request=None):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    old_status = project.status

    for field, value in data.items():

        if field == "name":
            value = value.strip()

        setattr(project, field, value)

    project.save()

    if old_status != project.status:

        activity_type = ProjectActivity.ActivityType.STATUS_CHANGED

    else:
        activity_type = ProjectActivity.ActivityType.OTHER

    create_project_activity(
        project,
        actor,
        activity_type,
        f"{actor.username} updated project {project.name}.",
        metadata={"updated_fields": list(data.keys())}
    )

    record_audit(
        actor,
        project.workspace,
        "PROJECT_UPDATED",
        f"{actor.username} updated project {project.name}.",
        object_type="Project",
        object_id=project.id,
        metadata={"updated_fields": list(data.keys())},
        request=request
    )

    return project


# -------------------------------------------------
# ARCHIVE PROJECT
# -------------------------------------------------

@transaction.atomic
def archive_project(actor, project, request=None):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    project.status = Project.Status.ARCHIVED
    project.save(update_fields=["status", "updated_at"])

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.STATUS_CHANGED,
        f"{actor.username} archived project {project.name}."
    )

    record_audit(
        actor,
        project.workspace,
        "PROJECT_UPDATED",
        f"{actor.username} archived project {project.name}.",
        object_type="Project",
        object_id=project.id,
        metadata={"status": "ARCHIVED"},
        request=request
    )

    return project


# -------------------------------------------------
# ADD PROJECT MEMBER
# -------------------------------------------------

@transaction.atomic
def add_project_member(
    actor,
    project,
    user_id,
    project_role,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    workspace_membership = WorkspaceMembership.objects.filter(
        workspace=project.workspace,
        user_id=user_id,
        status=WorkspaceMembership.Status.ACTIVE
    ).first()

    if not workspace_membership:
        raise ValidationError(
            "User must be an active workspace member first."
        )

    if (
        workspace_membership.role == WorkspaceMembership.Role.VIEWER
        and project_role != ProjectMembership.Role.VIEWER
    ):
        raise ValidationError(
            "Workspace viewers can only have project viewer access."
        )

    if project_role not in [
        ProjectMembership.Role.MEMBER,
        ProjectMembership.Role.VIEWER
    ]:
        raise ValidationError(
            "Use the project lead assignment endpoint to assign a lead."
        )

    existing = ProjectMembership.objects.select_for_update().filter(
        project=project,
        user_id=user_id
    ).first()

    if existing and existing.status == ProjectMembership.Status.ACTIVE:
        raise ValidationError(
            "User is already a project member."
        )

    if existing:

        existing.project_role = project_role
        existing.status = ProjectMembership.Status.ACTIVE
        existing.added_by = actor
        existing.save(
            update_fields=[
                "project_role",
                "status",
                "added_by",
                "updated_at"
            ]
        )

        membership = existing

    else:

        membership = ProjectMembership.objects.create(
            project=project,
            user_id=user_id,
            project_role=project_role,
            status=ProjectMembership.Status.ACTIVE,
            added_by=actor
        )

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.MEMBER_ADDED,
        f"A member was added to {project.name}.",
        metadata={
            "user_id": user_id,
            "role": project_role
        }
    )

    return membership


# -------------------------------------------------
# CHANGE PROJECT MEMBER ROLE
# -------------------------------------------------

@transaction.atomic
def change_project_member_role(
    actor,
    project,
    membership_id,
    new_role,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    target = ProjectMembership.objects.select_for_update().filter(
        pk=membership_id,
        project=project,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Project membership not found.")

    if target.project_role == ProjectMembership.Role.LEAD:
        raise ValidationError(
            "Assign another lead before changing the current lead role."
        )

    if new_role not in [
        ProjectMembership.Role.MEMBER,
        ProjectMembership.Role.VIEWER
    ]:
        raise ValidationError("Invalid project role.")

    workspace_membership = WorkspaceMembership.objects.get(
        workspace=project.workspace,
        user=target.user,
        status=WorkspaceMembership.Status.ACTIVE
    )

    if (
        workspace_membership.role == WorkspaceMembership.Role.VIEWER
        and new_role != ProjectMembership.Role.VIEWER
    ):
        raise ValidationError(
            "Workspace viewers cannot become project members or leads."
        )

    old_role = target.project_role

    target.project_role = new_role
    target.save(update_fields=["project_role", "updated_at"])

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.OTHER,
        f"Project member role changed.",
        metadata={
            "user_id": target.user_id,
            "old_role": old_role,
            "new_role": new_role
        }
    )

    return target


# -------------------------------------------------
# SET PROJECT LEAD
# -------------------------------------------------

@transaction.atomic
def set_project_lead(
    actor,
    project,
    membership_id,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    target = ProjectMembership.objects.select_for_update().filter(
        pk=membership_id,
        project=project,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Active project membership not found.")

    target_workspace_membership = WorkspaceMembership.objects.get(
        workspace=project.workspace,
        user=target.user,
        status=WorkspaceMembership.Status.ACTIVE
    )

    if target_workspace_membership.role == WorkspaceMembership.Role.VIEWER:
        raise ValidationError(
            "Workspace viewers cannot become project leads."
        )

    if target.project_role == ProjectMembership.Role.LEAD:
        raise ValidationError("This user is already the project lead.")

    current_lead = ProjectMembership.objects.select_for_update().filter(
        project=project,
        project_role=ProjectMembership.Role.LEAD,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if not current_lead:
        raise ValidationError(
            "The current project lead record is missing. Contact an administrator."
        )

    current_lead.project_role = ProjectMembership.Role.MEMBER
    current_lead.save(update_fields=["project_role", "updated_at"])

    target.project_role = ProjectMembership.Role.LEAD
    target.save(update_fields=["project_role", "updated_at"])

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.OTHER,
        "Project lead was changed.",
        metadata={
            "previous_lead_id": current_lead.user_id,
            "new_lead_id": target.user_id
        }
    )

    return target


# -------------------------------------------------
# REMOVE PROJECT MEMBER
# -------------------------------------------------

@transaction.atomic
def remove_project_member(
    actor,
    project,
    membership_id,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    target = ProjectMembership.objects.select_for_update().filter(
        pk=membership_id,
        project=project,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Project membership not found.")

    if target.user_id == actor.id:
        raise ValidationError(
            "You cannot remove yourself through this endpoint."
        )

    if target.project_role == ProjectMembership.Role.LEAD:
        raise ValidationError(
            "Transfer project leadership before removing the current lead."
        )

    target.status = ProjectMembership.Status.REMOVED
    target.save(update_fields=["status", "updated_at"])

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.MEMBER_REMOVED,
        f"A member was removed from {project.name}.",
        metadata={"user_id": target.user_id}
    )

    return target

# -------------------------------------------------
# VALIDATE TASK ASSIGNEE
# -------------------------------------------------

def validate_task_assignee(project, user_id):

    if user_id is None:
        return None

    user = User.objects.filter(pk=user_id).first()

    if not user:
        raise ValidationError("Assigned user does not exist.")

    membership = ProjectMembership.objects.filter(
        project=project,
        user=user,
        status=ProjectMembership.Status.ACTIVE
    ).first()

    if not membership:
        raise ValidationError(
            "Task can only be assigned to an active project member."
        )

    if membership.project_role == ProjectMembership.Role.VIEWER:
        raise ValidationError(
            "Tasks cannot be assigned to project viewers."
        )

    return user


# -------------------------------------------------
# CREATE TASK
# -------------------------------------------------

@transaction.atomic
def create_project_task(actor, project, data, request=None):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    require_project_manager(actor, project)

    assigned_to_id = data.pop("assigned_to_id", None)

    assigned_to = validate_task_assignee(
        project,
        assigned_to_id
    )

    task = ProjectTask.objects.create(
        project=project,
        created_by=actor,
        assigned_to=assigned_to,
        **data
    )

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.TASK_CREATED,
        f"{actor.username} created task {task.title}.",
        metadata={"task_id": task.id}
    )

    record_audit(
        actor,
        project.workspace,
        "OTHER",
        f"{actor.username} created task {task.title}.",
        object_type="ProjectTask",
        object_id=task.id,
        metadata={"event": "TASK_CREATED"},
        request=request
    )

    return task


# -------------------------------------------------
# UPDATE TASK
# -------------------------------------------------

@transaction.atomic
def update_project_task(actor, task, data, request=None):

    project = Project.objects.select_for_update().get(
        pk=task.project_id
    )

    task = ProjectTask.objects.select_for_update().get(
        pk=task.pk,
        project=project
    )

    workspace_membership, project_membership = (
        get_project_access(actor, project)
    )

    is_manager = (
        workspace_membership.role in ["OWNER", "ADMIN"]
        or (
            project_membership is not None
            and project_membership.project_role == "LEAD"
        )
    )

    if not is_manager:

        is_assigned_member = (
            project_membership is not None
            and project_membership.project_role
                == ProjectMembership.Role.MEMBER
            and task.assigned_to_id == actor.id
        )

        if not is_assigned_member:
            raise PermissionDenied(
                "You can only update tasks assigned to you."
            )

        if set(data.keys()) != {"status"}:
            raise PermissionDenied(
                "Project members can only update task status."
            )

        if data["status"] == ProjectTask.Status.CANCELLED:
            raise PermissionDenied(
                "Only project managers can cancel tasks."
            )

    ensure_workspace_active(project.workspace)

    if project.status == Project.Status.ARCHIVED:
        raise ValidationError("Archived projects cannot be modified.")

    if "assigned_to_id" in data:

        assigned_to = validate_task_assignee(
            project,
            data.pop("assigned_to_id")
        )

        task.assigned_to = assigned_to

    for field, value in data.items():
        setattr(task, field, value)

    if task.status == ProjectTask.Status.DONE:

        if not task.completed_at:
            task.completed_at = timezone.now()

    else:
        task.completed_at = None

    task.save()

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.TASK_UPDATED,
        f"{actor.username} updated task {task.title}.",
        metadata={
            "task_id": task.id,
            "status": task.status
        }
    )

    record_audit(
        actor,
        project.workspace,
        "OTHER",
        f"{actor.username} updated task {task.title}.",
        object_type="ProjectTask",
        object_id=task.id,
        metadata={
            "event": "TASK_UPDATED",
            "updated_fields": list(data.keys())
        },
        request=request
    )

    return task


# =================================================
# PROJECT DECISION MANAGEMENT
# =================================================


# -------------------------------------------------
# CREATE DECISION
# -------------------------------------------------

@transaction.atomic
def create_project_decision(actor, project, data, request=None):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    workspace_membership, project_membership = get_project_access(
        actor,
        project
    )

    # Viewers cannot propose decisions.
    if workspace_membership.role == WorkspaceMembership.Role.VIEWER:
        raise PermissionDenied(
            "Viewers cannot create project decisions."
        )

    if (
        project_membership is not None
        and project_membership.project_role == ProjectMembership.Role.VIEWER
    ):
        raise PermissionDenied(
            "Project viewers cannot create decisions."
        )

    ensure_workspace_active(project.workspace)

    if project.status == Project.Status.ARCHIVED:
        raise ValidationError(
            "Archived projects cannot be modified."
        )

    decision = ProjectDecision.objects.create(
        project=project,
        created_by=actor,
        status=ProjectDecision.DecisionStatus.PROPOSED,
        **data
    )

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.DECISION_RECORDED,
        f"{actor.username} proposed decision: {decision.title}.",
        metadata={
            "decision_id": decision.id,
            "status": decision.status
        }
    )

    record_audit(
        actor,
        project.workspace,
        "OTHER",
        f"{actor.username} proposed decision {decision.title}.",
        object_type="ProjectDecision",
        object_id=decision.id,
        metadata={
            "event": "DECISION_CREATED"
        },
        request=request
    )

    return decision


# -------------------------------------------------
# UPDATE PROPOSED DECISION
# -------------------------------------------------

@transaction.atomic
def update_project_decision(
    actor,
    project,
    decision,
    data,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    decision = ProjectDecision.objects.select_for_update().get(
        pk=decision.pk,
        project=project
    )

    workspace_membership, project_membership = get_project_access(
        actor,
        project
    )

    is_workspace_manager = workspace_membership.role in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN
    ]

    is_project_lead = (
        project_membership is not None
        and project_membership.project_role == ProjectMembership.Role.LEAD
    )

    is_creator = decision.created_by_id == actor.id

    is_project_member = (
        project_membership is not None
        and project_membership.project_role == ProjectMembership.Role.MEMBER
    )

    if not (
        is_workspace_manager
        or is_project_lead
        or (is_creator and is_project_member)
    ):
        raise PermissionDenied(
            "You cannot modify this decision."
        )

    ensure_workspace_active(project.workspace)

    if project.status == Project.Status.ARCHIVED:
        raise ValidationError(
            "Archived projects cannot be modified."
        )

    if decision.status != ProjectDecision.DecisionStatus.PROPOSED:
        raise ValidationError(
            "Only proposed decisions can be edited."
        )

    for field, value in data.items():
        setattr(decision, field, value)

    decision.save()

    record_audit(
        actor,
        project.workspace,
        "OTHER",
        f"{actor.username} updated decision {decision.title}.",
        object_type="ProjectDecision",
        object_id=decision.id,
        metadata={
            "event": "DECISION_UPDATED",
            "updated_fields": list(data.keys())
        },
        request=request
    )

    return decision


# -------------------------------------------------
# CHANGE DECISION STATUS
# -------------------------------------------------

@transaction.atomic
def transition_project_decision(
    actor,
    project,
    decision,
    new_status,
    request=None
):

    project = Project.objects.select_for_update().get(
        pk=project.pk
    )

    decision = ProjectDecision.objects.select_for_update().get(
        pk=decision.pk,
        project=project
    )

    require_project_manager(actor, project)

    ensure_workspace_active(project.workspace)

    if project.status == Project.Status.ARCHIVED:
        raise ValidationError(
            "Archived projects cannot be modified."
        )

    current_status = decision.status

    allowed_transitions = {
        ProjectDecision.DecisionStatus.PROPOSED: [
            ProjectDecision.DecisionStatus.ACCEPTED,
            ProjectDecision.DecisionStatus.REJECTED
        ],

        ProjectDecision.DecisionStatus.ACCEPTED: [
            ProjectDecision.DecisionStatus.SUPERSEDED
        ]
    }

    allowed_next_statuses = allowed_transitions.get(
        current_status,
        []
    )

    if new_status not in allowed_next_statuses:
        raise ValidationError(
            f"Transition from {current_status} to {new_status} is not allowed."
        )

    decision.status = new_status
    decision.decision_date = timezone.now()

    decision.save(
        update_fields=[
            "status",
            "decision_date",
            "updated_at"
        ]
    )

    create_project_activity(
        project,
        actor,
        ProjectActivity.ActivityType.DECISION_RECORDED,
        f"{actor.username} changed decision status to {new_status}.",
        metadata={
            "decision_id": decision.id,
            "old_status": current_status,
            "new_status": new_status
        }
    )

    record_audit(
        actor,
        project.workspace,
        "OTHER",
        f"{actor.username} changed decision {decision.title} status.",
        object_type="ProjectDecision",
        object_id=decision.id,
        metadata={
            "event": "DECISION_STATUS_CHANGED",
            "old_status": current_status,
            "new_status": new_status
        },
        request=request
    )

    return decision