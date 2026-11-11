from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from projects.models import Project, ProjectMembership
from workspaces.models import WorkspaceMembership
from workspaces.services import (
    ensure_workspace_active,
    get_membership,
    record_audit,
)

from .models import KnowledgeItem, KnowledgeConflict


WORKSPACE_REVIEW_ROLES = {
    WorkspaceMembership.Role.OWNER,
    WorkspaceMembership.Role.ADMIN,
}


def get_project_access(actor, project_id, reviewer=False):
    project = Project.objects.select_related("workspace").filter(
        pk=project_id
    ).first()
    if not project:
        raise NotFound("Project not found.")

    workspace_membership = get_membership(actor, project.workspace)
    ensure_workspace_active(project.workspace)

    project_membership = None
    if workspace_membership.role not in WORKSPACE_REVIEW_ROLES:
        project_membership = ProjectMembership.objects.filter(
            project=project,
            user=actor,
            status=ProjectMembership.Status.ACTIVE,
        ).first()
        if not project_membership:
            raise PermissionDenied("You are not an active member of this project.")

    if reviewer:
        is_workspace_reviewer = workspace_membership.role in WORKSPACE_REVIEW_ROLES
        is_project_lead = (
            project_membership is not None
            and project_membership.project_role == ProjectMembership.Role.LEAD
        )
        if not (is_workspace_reviewer or is_project_lead):
            raise PermissionDenied(
                "Only the workspace owner/admin or project lead can review knowledge and resolve conflicts."
            )
        if project.status == Project.Status.ARCHIVED:
            raise PermissionDenied("Archived projects cannot be changed.")

    return project


def get_knowledge_item_for_actor(actor, item_id, reviewer=False):
    item = KnowledgeItem.objects.select_related(
        "project__workspace",
        "analysis_run",
        "assigned_to",
    ).filter(pk=item_id).first()
    if not item:
        raise NotFound("Knowledge item not found.")

    get_project_access(actor, item.project_id, reviewer=reviewer)
    return item


def get_conflict_for_actor(actor, conflict_id, reviewer=False, lock=False):
    queryset = KnowledgeConflict.objects.select_related(
        "project__workspace",
        "knowledge_item_a",
        "knowledge_item_b",
        "resolved_by",
    )
    if lock:
        queryset = queryset.select_for_update()

    conflict = queryset.filter(pk=conflict_id).first()
    if not conflict:
        raise NotFound("Knowledge conflict not found.")

    get_project_access(actor, conflict.project_id, reviewer=reviewer)
    return conflict


def append_review_history(item, actor, action, note=""):
    metadata = dict(item.metadata or {})
    history = list(metadata.get("human_review_history", []))
    history.append({
        "action": action,
        "actor_id": actor.id,
        "actor_username": actor.username,
        "at": timezone.now().isoformat(),
        "note": note,
    })
    metadata["human_review_history"] = history[-25:]
    item.metadata = metadata


def audit_knowledge_action(actor, item, action, description, request=None, metadata=None):
    record_audit(
        actor=actor,
        workspace=item.project.workspace,
        action="OTHER",
        description=description,
        object_type="KnowledgeItem",
        object_id=item.id,
        metadata={
            "event": action,
            **(metadata or {}),
        },
        request=request,
    )


@transaction.atomic
def update_knowledge_item(actor, item_id, data, request=None):
    item = get_knowledge_item_for_actor(actor, item_id, reviewer=True)

    for field, value in data.items():
        if field == "assigned_to":
            item.assigned_to = value
        else:
            setattr(item, field, value)

    item.full_clean(exclude=["analysis_run"])
    item.save()

    append_review_history(item, actor, "EDITED", "Reviewer updated knowledge fields.")
    item.save(update_fields=["metadata", "updated_at"])

    audit_knowledge_action(
        actor,
        item,
        "KNOWLEDGE_ITEM_UPDATED",
        f"Reviewer updated knowledge item: {item.title}",
        request=request,
        metadata={"updated_fields": sorted(data.keys())},
    )
    return item


@transaction.atomic
def review_knowledge_item(actor, item_id, approved, note="", request=None):
    item = get_knowledge_item_for_actor(actor, item_id, reviewer=True)

    if item.verification_status == KnowledgeItem.VerificationStatus.SUPERSEDED:
        raise ValidationError("A superseded knowledge item cannot be reviewed again.")

    if approved:
        item.verification_status = KnowledgeItem.VerificationStatus.VERIFIED
        action = "VERIFIED"
        description = f"Verified knowledge item: {item.title}"
    else:
        item.verification_status = KnowledgeItem.VerificationStatus.REJECTED
        action = "REJECTED"
        description = f"Rejected knowledge item: {item.title}"

    append_review_history(item, actor, action, note)
    item.save(update_fields=["verification_status", "metadata", "updated_at"])

    audit_knowledge_action(
        actor,
        item,
        f"KNOWLEDGE_ITEM_{action}",
        description,
        request=request,
        metadata={"review_note": note},
    )
    return item


@transaction.atomic
def resolve_knowledge_conflict(actor, conflict_id, data, request=None):
    conflict = get_conflict_for_actor(
        actor,
        conflict_id,
        reviewer=True,
        lock=True,
    )

    if conflict.resolution_status in {
        KnowledgeConflict.ResolutionStatus.RESOLVED,
        KnowledgeConflict.ResolutionStatus.ACCEPTED_BOTH,
        KnowledgeConflict.ResolutionStatus.DISMISSED,
    }:
        raise ValidationError("This conflict has already been resolved and cannot be changed.")

    new_status = data["resolution_status"]
    notes = data.get("resolution_notes", "").strip()
    keep_id = data.get("keep_knowledge_item_id")
    item_a = conflict.knowledge_item_a
    item_b = conflict.knowledge_item_b

    if new_status == KnowledgeConflict.ResolutionStatus.RESOLVED:
        if keep_id == item_a.id:
            keep_item, superseded_item = item_a, item_b
        elif keep_id == item_b.id:
            keep_item, superseded_item = item_b, item_a
        else:
            raise ValidationError({
                "keep_knowledge_item_id": "The selected item must be one of the two items in this conflict."
            })

        keep_item.verification_status = KnowledgeItem.VerificationStatus.VERIFIED
        superseded_item.verification_status = KnowledgeItem.VerificationStatus.SUPERSEDED
        keep_item.save(update_fields=["verification_status", "updated_at"])
        superseded_item.save(update_fields=["verification_status", "updated_at"])

    elif new_status == KnowledgeConflict.ResolutionStatus.ACCEPTED_BOTH:
        item_a.verification_status = KnowledgeItem.VerificationStatus.VERIFIED
        item_b.verification_status = KnowledgeItem.VerificationStatus.VERIFIED
        item_a.save(update_fields=["verification_status", "updated_at"])
        item_b.save(update_fields=["verification_status", "updated_at"])

    conflict.resolution_status = new_status
    conflict.resolution_notes = notes
    if new_status == KnowledgeConflict.ResolutionStatus.UNDER_REVIEW:
        conflict.resolved_by = None
        conflict.resolved_at = None
    else:
        conflict.resolved_by = actor
        conflict.resolved_at = timezone.now()

    conflict.save(update_fields=[
        "resolution_status",
        "resolution_notes",
        "resolved_by",
        "resolved_at",
        "updated_at",
    ])

    record_audit(
        actor=actor,
        workspace=conflict.project.workspace,
        action="OTHER",
        description=(
            f"Knowledge conflict {conflict.id} set to {new_status} "
            f"for project {conflict.project.name}."
        ),
        object_type="KnowledgeConflict",
        object_id=conflict.id,
        metadata={
            "event": "KNOWLEDGE_CONFLICT_RESOLVED",
            "resolution_status": new_status,
            "keep_knowledge_item_id": keep_id,
            "resolution_notes": notes,
        },
        request=request,
    )

    return conflict
