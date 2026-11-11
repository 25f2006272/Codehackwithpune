from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from projects.models import Project, ProjectMembership
from workspaces.models import WorkspaceMembership
from workspaces.services import get_membership, ensure_workspace_active, record_audit
from ai_engine.models import KnowledgeItem
from .models import Handover, HandoverItem, HandoverVersion, HandoverAcknowledgement


EDITABLE_STATUSES = {Handover.Status.DRAFT, Handover.Status.CHANGES_REQUESTED}


def get_project_or_404(project_id):
    try:
        return Project.objects.select_related("workspace").get(pk=project_id)
    except Project.DoesNotExist:
        raise NotFound("Project not found.")


def workspace_membership(actor, workspace):
    membership = get_membership(actor, workspace)
    ensure_workspace_active(workspace)
    return membership


def project_role(actor, project):
    return ProjectMembership.objects.filter(
        project=project, user=actor, status="ACTIVE"
    ).values_list("project_role", flat=True).first()


def can_manage_project(actor, project):
    membership = workspace_membership(actor, project.workspace)
    if membership.role in ("OWNER", "ADMIN"):
        return True
    return project_role(actor, project) == "LEAD"


def require_project_read(actor, project):
    membership = workspace_membership(actor, project.workspace)
    if membership.role in ("OWNER", "ADMIN"):
        return
    if project_role(actor, project) is None:
        raise PermissionDenied("You are not an active member of this project.")


def require_project_manager(actor, project):
    if not can_manage_project(actor, project):
        raise PermissionDenied("Only workspace owners/admins or project leads can manage handovers.")


def require_handover_read(actor, handover):
    require_project_read(actor, handover.project)


def require_handover_edit(actor, handover):
    require_handover_read(actor, handover)
    if not can_manage_project(actor, handover.project):
        raise PermissionDenied("Only workspace owners/admins or project leads can edit this handover.")
    if handover.status not in EDITABLE_STATUSES:
        raise ValidationError("This handover can no longer be edited in its current status.")


def validate_participant(user_id, project, label):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if not user:
        raise ValidationError({f"{label}_member_id": "User not found or inactive."})
    # A handover participant must be active in both the project and
    # its parent workspace. This prevents stale project memberships
    # from being used after workspace access has been revoked.
    try:
        get_membership(user, project.workspace)
        ensure_workspace_active(project.workspace)
    except PermissionDenied as exc:
        raise ValidationError({
            f"{label}_member_id": "User must be an active member of this workspace."
        }) from exc

    membership = ProjectMembership.objects.filter(
        project=project, user=user, status="ACTIVE"
    ).exists()
    if not membership:
        raise ValidationError({f"{label}_member_id": "User must be an active member of this project."})
    return user


def knowledge_snapshot(item):
    evidence = []
    for row in item.evidence.select_related(
        "document_chunk__extraction__file_version__file_asset"
    ).all():
        file_asset = row.document_chunk.extraction.file_version.file_asset
        evidence.append({
            "filename": file_asset.name,
            "quoted_text": row.quoted_text,
            "page_number": row.document_chunk.page_number,
            "chunk_id": row.document_chunk_id,
        })
    return {
        "knowledge_item_id": item.id,
        "item_type": item.item_type,
        "title": item.title,
        "description": item.description,
        "priority": item.priority,
        "confidence_score": str(item.confidence_score) if item.confidence_score is not None else None,
        "evidence": evidence,
    }


def build_snapshot(handover):
    return {
        "handover": {
            "id": handover.id,
            "project_id": handover.project_id,
            "project_name": handover.project.name,
            "title": handover.title,
            "summary": handover.summary,
            "departing_member_id": handover.departing_member_id,
            "departing_member": handover.departing_member.username,
            "incoming_member_id": handover.incoming_member_id,
            "incoming_member": handover.incoming_member.username,
            "status": handover.status,
        },
        "items": list(handover.items.values(
            "id", "knowledge_item_id", "category", "title", "content",
            "priority", "sort_order", "source_snapshot"
        )),
    }


@transaction.atomic
def create_handover(actor, project, data, request=None):
    require_project_manager(actor, project)
    if project.status == "ARCHIVED":
        raise ValidationError("Cannot create a handover for an archived project.")

    departing = validate_participant(data["departing_member_id"], project, "departing")
    incoming = validate_participant(data["incoming_member_id"], project, "incoming")
    if departing.pk == incoming.pk:
        raise ValidationError("Departing and incoming members must be different.")

    selected_ids = data.get("knowledge_item_ids", [])
    selected = list(KnowledgeItem.objects.filter(
        id__in=selected_ids, project=project,
        verification_status=KnowledgeItem.VerificationStatus.VERIFIED,
    ).prefetch_related("evidence__document_chunk__extraction__file_version__file_asset"))
    if len(selected) != len(selected_ids):
        raise ValidationError({
            "knowledge_item_ids": "Every selected knowledge item must exist in this project and have VERIFIED status. Rejected, superseded, and unreviewed items cannot be included."
        })

    handover = Handover.objects.create(
        project=project,
        title=data["title"],
        departing_member=departing,
        incoming_member=incoming,
        created_by=actor,
        summary=data.get("summary", ""),
        status=Handover.Status.DRAFT,
    )

    for index, item in enumerate(selected):
        source = knowledge_snapshot(item)
        category = item.item_type if item.item_type in HandoverItem.Category.values else HandoverItem.Category.OTHER
        HandoverItem.objects.create(
            handover=handover,
            knowledge_item=item,
            category=category,
            title=item.title,
            content=item.description,
            priority=item.priority if item.priority in HandoverItem.Priority.values else HandoverItem.Priority.MEDIUM,
            sort_order=index,
            source_snapshot=source,
        )

    for index, item_data in enumerate(data.get("items", []), start=len(selected)):
        allowed = {"category", "title", "content", "priority", "sort_order"}
        if set(item_data) - allowed:
            raise ValidationError({"items": "Manual item contains unsupported fields."})
        serializer_data = dict(item_data)
        serializer_data.setdefault("sort_order", index)
        from .serializers import HandoverItemCreateSerializer
        serializer = HandoverItemCreateSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        HandoverItem.objects.create(handover=handover, **serializer.validated_data)

    create_version(handover, actor, "Initial handover draft")
    record_audit(
        actor, project.workspace, "HANDOVER_CREATED",
        f"Created handover: {handover.title}",
        object_type="Handover", object_id=handover.id, request=request,
    )
    return handover


def create_version(handover, actor, change_summary=""):
    latest = handover.versions.order_by("-version_number").first()
    number = (latest.version_number + 1) if latest else 1
    return HandoverVersion.objects.create(
        handover=handover,
        version_number=number,
        snapshot=build_snapshot(handover),
        change_summary=change_summary,
        created_by=actor,
    )


def log_handover(actor, handover, action, description, request=None, metadata=None):
    record_audit(
        actor, handover.project.workspace, action, description,
        object_type="Handover", object_id=handover.id,
        metadata=metadata or {}, request=request,
    )


def require_latest_knowledge_still_verified(handover):
    linked = handover.items.exclude(knowledge_item__isnull=True).select_related("knowledge_item")
    for item in linked:
        if item.knowledge_item.verification_status != KnowledgeItem.VerificationStatus.VERIFIED:
            raise ValidationError(
                f'Knowledge item "{item.title}" is no longer verified. Remove it from the draft before submitting.'
            )


@transaction.atomic
def submit_handover(actor, handover, request=None):
    require_handover_edit(actor, handover)
    if not handover.items.exists():
        raise ValidationError("Add at least one handover item before submitting for review.")
    require_latest_knowledge_still_verified(handover)
    handover.status = Handover.Status.IN_REVIEW
    handover.submitted_at = timezone.now()
    handover.save(update_fields=["status", "submitted_at", "updated_at"])
    create_version(handover, actor, "Submitted for review")
    log_handover(actor, handover, "HANDOVER_SUBMITTED", f"Submitted handover for review: {handover.title}", request)
    return handover


@transaction.atomic
def review_handover(actor, handover, decision, comments="", request=None):
    require_handover_read(actor, handover)
    require_project_manager(actor, handover.project)
    if handover.status != Handover.Status.IN_REVIEW:
        raise ValidationError("Only handovers in IN_REVIEW status can be reviewed.")
    version = handover.versions.order_by("-version_number").first()
    from .models import HandoverReview
    review = HandoverReview.objects.create(
        handover=handover,
        reviewer=actor,
        reviewed_version=version,
        decision=decision,
        comments=comments,
    )
    if decision == HandoverReview.Decision.APPROVED:
        handover.status = Handover.Status.APPROVED
        handover.approved_at = timezone.now()
    elif decision == HandoverReview.Decision.CHANGES_REQUESTED:
        handover.status = Handover.Status.CHANGES_REQUESTED
        handover.approved_at = None
    else:
        handover.status = Handover.Status.REJECTED
    handover.save(update_fields=["status", "approved_at", "updated_at"])
    log_handover(actor, handover, "HANDOVER_REVIEWED", f"Handover review decision: {decision}", request, {"decision": decision, "review_id": review.id})
    return review


@transaction.atomic
def share_handover(actor, handover, request=None):
    require_handover_read(actor, handover)
    require_project_manager(actor, handover.project)
    if handover.status != Handover.Status.APPROVED:
        raise ValidationError("Only an APPROVED handover can be shared with the incoming member.")
    HandoverAcknowledgement.objects.get_or_create(
        handover=handover,
        recipient=handover.incoming_member,
        defaults={"status": HandoverAcknowledgement.Status.PENDING},
    )
    handover.status = Handover.Status.SHARED
    handover.shared_at = timezone.now()
    handover.save(update_fields=["status", "shared_at", "updated_at"])
    log_handover(actor, handover, "HANDOVER_SHARED", f"Shared handover with {handover.incoming_member.username}", request)
    return handover


@transaction.atomic
def acknowledge_handover(actor, handover, status, comments="", request=None):
    require_handover_read(actor, handover)
    if actor.pk != handover.incoming_member_id:
        raise PermissionDenied("Only the assigned incoming member can acknowledge this handover.")
    if handover.status != Handover.Status.SHARED:
        raise ValidationError("Only a SHARED handover can be acknowledged.")
    ack, _ = HandoverAcknowledgement.objects.get_or_create(
        handover=handover,
        recipient=actor,
        defaults={"status": HandoverAcknowledgement.Status.PENDING},
    )
    ack.status = status
    ack.comments = comments
    ack.acknowledged_at = timezone.now() if status == HandoverAcknowledgement.Status.ACKNOWLEDGED else None
    ack.save(update_fields=["status", "comments", "acknowledged_at", "updated_at"])
    if status == HandoverAcknowledgement.Status.ACKNOWLEDGED:
        handover.status = Handover.Status.ACKNOWLEDGED
        handover.save(update_fields=["status", "updated_at"])
    log_handover(actor, handover, "HANDOVER_ACKNOWLEDGED" if status == HandoverAcknowledgement.Status.ACKNOWLEDGED else "HANDOVER_CLARIFICATION_REQUESTED", f"Incoming member response: {status}", request, {"status": status})
    return ack
