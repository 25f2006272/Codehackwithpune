import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from .models import Workspace, WorkspaceMembership, WorkspaceInvitation


User = get_user_model()


def get_membership(user, workspace):
    membership = WorkspaceMembership.objects.filter(
        workspace=workspace,
        user=user,
        status=WorkspaceMembership.Status.ACTIVE
    ).first()

    if not membership:
        raise PermissionDenied("You are not an active workspace member.")

    # Prevent owner and membership records from silently diverging.
    if membership.role == WorkspaceMembership.Role.OWNER:
        if workspace.owner_id != user.id:
            raise PermissionDenied("Workspace ownership records are inconsistent.")

    if workspace.owner_id == user.id:
        if membership.role != WorkspaceMembership.Role.OWNER:
            raise PermissionDenied("Workspace ownership records are inconsistent.")

    return membership


def require_manager(user, workspace):
    membership = get_membership(user, workspace)

    if membership.role not in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN
    ]:
        raise PermissionDenied("Only workspace owners and admins can perform this action.")

    return membership


def require_owner(user, workspace):
    membership = get_membership(user, workspace)

    if (
        membership.role != WorkspaceMembership.Role.OWNER
        or workspace.owner_id != user.id
    ):
        raise PermissionDenied("Only the workspace owner can perform this action.")

    return membership


def ensure_workspace_active(workspace):
    if workspace.status != Workspace.Status.ACTIVE:
        raise ValidationError("This workspace is not active.")


def record_audit(
    actor,
    workspace,
    action,
    description,
    object_type="Workspace",
    object_id="",
    metadata=None,
    request=None
):
    from audit.models import AuditLog

    ip_address = None
    user_agent = ""

    if request:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    AuditLog.objects.create(
        actor=actor,
        workspace=workspace,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        description=description,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent
    )


# --------------------------------------------------
# CREATE WORKSPACE
# --------------------------------------------------

@transaction.atomic
def create_workspace(actor, validated_data, request=None):

    name = validated_data["name"].strip()

    base_slug = slugify(name)[:160] or "workspace"
    slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

    workspace = Workspace.objects.create(
        name=name,
        slug=slug,
        description=validated_data.get("description", ""),
        workspace_type=validated_data.get(
            "workspace_type",
            Workspace.WorkspaceType.OTHER
        ),
        logo_url=validated_data.get("logo_url", ""),
        owner=actor,
        created_by=actor
    )

    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=actor,
        role=WorkspaceMembership.Role.OWNER,
        status=WorkspaceMembership.Status.ACTIVE,
        added_by=actor
    )

    record_audit(
        actor=actor,
        workspace=workspace,
        action="WORKSPACE_CREATED",
        description=f"{actor.username} created workspace {workspace.name}.",
        object_id=workspace.id,
        request=request
    )

    return workspace


# --------------------------------------------------
# UPDATE WORKSPACE
# --------------------------------------------------

@transaction.atomic
def update_workspace(actor, workspace, data, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    membership = get_membership(actor, workspace)

    if membership.role not in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN
    ]:
        raise PermissionDenied("You cannot update this workspace.")

    ensure_workspace_active(workspace)

    for field, value in data.items():
        if field == "name":
            value = value.strip()

        setattr(workspace, field, value)

    workspace.save()

    record_audit(
        actor,
        workspace,
        "WORKSPACE_UPDATED",
        f"{actor.username} updated workspace {workspace.name}.",
        object_id=workspace.id,
        metadata={"updated_fields": list(data.keys())},
        request=request
    )

    return workspace


# --------------------------------------------------
# ARCHIVE WORKSPACE
# --------------------------------------------------

@transaction.atomic
def archive_workspace(actor, workspace, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    require_owner(actor, workspace)

    if workspace.status == Workspace.Status.ARCHIVED:
        return workspace

    ensure_workspace_active(workspace)

    workspace.status = Workspace.Status.ARCHIVED
    workspace.save(update_fields=["status", "updated_at"])

    record_audit(
        actor,
        workspace,
        "WORKSPACE_UPDATED",
        f"{actor.username} archived workspace {workspace.name}.",
        object_id=workspace.id,
        metadata={"operation": "ARCHIVED"},
        request=request
    )

    return workspace


# --------------------------------------------------
# INVITE MEMBER
# --------------------------------------------------

@transaction.atomic
def invite_member(actor, workspace, email, invited_role, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    actor_membership = require_manager(actor, workspace)
    ensure_workspace_active(workspace)

    email = email.strip().lower()

    allowed_roles = {
        WorkspaceMembership.Role.ADMIN,
        WorkspaceMembership.Role.MEMBER,
        WorkspaceMembership.Role.VIEWER
    }

    if invited_role not in allowed_roles:
        raise ValidationError("Invalid invitation role.")

    # Admins cannot appoint other admins.
    if (
        actor_membership.role == WorkspaceMembership.Role.ADMIN
        and invited_role == WorkspaceMembership.Role.ADMIN
    ):
        raise PermissionDenied("Only the owner can invite workspace admins.")

    invited_user = User.objects.filter(email__iexact=email).first()

    if invited_user:
        existing_membership = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=invited_user,
            status=WorkspaceMembership.Status.ACTIVE
        ).exists()

        if existing_membership:
            raise ValidationError("This user is already a workspace member.")

    now = timezone.now()

    old_invitation = WorkspaceInvitation.objects.select_for_update().filter(
        workspace=workspace,
        email__iexact=email,
        status=WorkspaceInvitation.Status.PENDING
    ).first()

    if old_invitation:

        if old_invitation.expires_at > now:
            raise ValidationError("A pending invitation already exists for this email.")

        old_invitation.status = WorkspaceInvitation.Status.EXPIRED
        old_invitation.save(update_fields=["status", "updated_at"])

    try:
        with transaction.atomic():
            invitation = WorkspaceInvitation.objects.create(
                workspace=workspace,
                email=email,
                invited_by=actor,
                invited_role=invited_role,
                expires_at=now + timedelta(days=7)
            )
    except Exception as exc:
        # Do not expose database-level details to API consumers.
        raise ValidationError("Could not create the invitation.") from exc

    record_audit(
        actor,
        workspace,
        "MEMBER_INVITED",
        f"{actor.username} invited {email}.",
        object_type="WorkspaceInvitation",
        object_id=invitation.id,
        metadata={"invited_role": invited_role},
        request=request
    )

    return invitation


# --------------------------------------------------
# GET WORKSPACE INVITATIONS
# --------------------------------------------------

def get_workspace_invitations(actor, workspace):

    require_manager(actor, workspace)

    now = timezone.now()

    WorkspaceInvitation.objects.filter(
        workspace=workspace,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at__lte=now
    ).update(status=WorkspaceInvitation.Status.EXPIRED)

    return WorkspaceInvitation.objects.filter(
        workspace=workspace
    ).select_related("invited_by").order_by("-created_at")


# --------------------------------------------------
# REVOKE INVITATION
# --------------------------------------------------

@transaction.atomic
def revoke_invitation(actor, workspace, invitation_id, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    actor_membership = require_manager(actor, workspace)
    ensure_workspace_active(workspace)

    invitation = WorkspaceInvitation.objects.select_for_update().filter(
        pk=invitation_id,
        workspace=workspace
    ).first()

    if not invitation:
        raise NotFound("Invitation not found.")

    if invitation.status != WorkspaceInvitation.Status.PENDING:
        raise ValidationError("This invitation is no longer pending.")

    if (
        actor_membership.role == WorkspaceMembership.Role.ADMIN
        and invitation.invited_role == WorkspaceMembership.Role.ADMIN
    ):
        raise PermissionDenied("Only the owner can revoke admin invitations.")

    invitation.status = WorkspaceInvitation.Status.REVOKED
    invitation.save(update_fields=["status", "updated_at"])

    record_audit(
        actor,
        workspace,
        "OTHER",
        f"{actor.username} revoked an invitation.",
        object_type="WorkspaceInvitation",
        object_id=invitation.id,
        metadata={"event": "INVITATION_REVOKED"},
        request=request
    )

    return invitation


# --------------------------------------------------
# MY INVITATIONS
# --------------------------------------------------

def get_my_invitations(user):

    if not user.email:
        return WorkspaceInvitation.objects.none()

    now = timezone.now()

    WorkspaceInvitation.objects.filter(
        email__iexact=user.email,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at__lte=now
    ).update(status=WorkspaceInvitation.Status.EXPIRED)

    return WorkspaceInvitation.objects.filter(
        email__iexact=user.email,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at__gt=now
    ).select_related("workspace", "invited_by").order_by("-created_at")


# --------------------------------------------------
# ACCEPT INVITATION
# --------------------------------------------------

@transaction.atomic
def accept_invitation(user, token, request=None):

    invitation = WorkspaceInvitation.objects.select_for_update().filter(
        token=token
    ).first()

    if not invitation:
        raise NotFound("Invitation not found.")

    if invitation.status != WorkspaceInvitation.Status.PENDING:
        raise ValidationError("This invitation is no longer pending.")

    if not user.email or user.email.lower() != invitation.email.lower():
        raise PermissionDenied("This invitation belongs to a different email address.")

    now = timezone.now()

    if invitation.expires_at <= now:
        invitation.status = WorkspaceInvitation.Status.EXPIRED
        invitation.save(update_fields=["status", "updated_at"])

        # Raise outside the atomic block so the expired status is retained.
        expired = True

    else:
        expired = False

        workspace = Workspace.objects.select_for_update().get(
            pk=invitation.workspace_id
        )

        ensure_workspace_active(workspace)

        if workspace.owner_id == user.id:
            raise ValidationError("The workspace owner cannot accept an invitation.")

        membership = WorkspaceMembership.objects.select_for_update().filter(
            workspace=workspace,
            user=user
        ).first()

        if membership and membership.status == WorkspaceMembership.Status.ACTIVE:
            raise ValidationError("You are already a workspace member.")

        if membership:
            membership.role = invitation.invited_role
            membership.status = WorkspaceMembership.Status.ACTIVE
            membership.added_by = invitation.invited_by
            membership.joined_at = now
            membership.save(
                update_fields=[
                    "role",
                    "status",
                    "added_by",
                    "joined_at",
                    "updated_at"
                ]
            )
        else:
            membership = WorkspaceMembership.objects.create(
                workspace=workspace,
                user=user,
                role=invitation.invited_role,
                status=WorkspaceMembership.Status.ACTIVE,
                added_by=invitation.invited_by
            )

        invitation.status = WorkspaceInvitation.Status.ACCEPTED
        invitation.accepted_by = user
        invitation.accepted_at = now

        invitation.save(
            update_fields=[
                "status",
                "accepted_by",
                "accepted_at",
                "updated_at"
            ]
        )

        record_audit(
            user,
            workspace,
            "MEMBER_JOINED",
            f"{user.username} joined the workspace.",
            object_type="WorkspaceMembership",
            object_id=membership.id,
            request=request
        )

    if expired:
        raise ValidationError("This invitation has expired.")

    return membership


# --------------------------------------------------
# DECLINE INVITATION
# --------------------------------------------------

@transaction.atomic
def decline_invitation(user, token, request=None):

    invitation = WorkspaceInvitation.objects.select_for_update().filter(
        token=token
    ).first()

    if not invitation:
        raise NotFound("Invitation not found.")

    if invitation.status != WorkspaceInvitation.Status.PENDING:
        raise ValidationError("This invitation is no longer pending.")

    if not user.email or user.email.lower() != invitation.email.lower():
        raise PermissionDenied("This invitation belongs to a different email address.")

    if invitation.expires_at <= timezone.now():
        invitation.status = WorkspaceInvitation.Status.EXPIRED
        invitation.save(update_fields=["status", "updated_at"])
        raise ValidationError("This invitation has expired.")

    invitation.status = WorkspaceInvitation.Status.DECLINED
    invitation.save(update_fields=["status", "updated_at"])

    record_audit(
        user,
        invitation.workspace,
        "OTHER",
        f"{user.username} declined a workspace invitation.",
        object_type="WorkspaceInvitation",
        object_id=invitation.id,
        metadata={"event": "INVITATION_DECLINED"},
        request=request
    )


# --------------------------------------------------
# CHANGE MEMBER ROLE
# --------------------------------------------------

@transaction.atomic
def change_member_role(actor, workspace, membership_id, new_role, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    actor_membership = require_manager(actor, workspace)
    ensure_workspace_active(workspace)

    target = WorkspaceMembership.objects.select_for_update().filter(
        pk=membership_id,
        workspace=workspace,
        status=WorkspaceMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Active workspace membership not found.")

    if target.role == WorkspaceMembership.Role.OWNER:
        raise PermissionDenied("The workspace owner's role cannot be changed here.")

    if new_role not in [
        WorkspaceMembership.Role.ADMIN,
        WorkspaceMembership.Role.MEMBER,
        WorkspaceMembership.Role.VIEWER
    ]:
        raise ValidationError("Invalid member role.")

    if actor_membership.role == WorkspaceMembership.Role.ADMIN:

        if target.role not in [
            WorkspaceMembership.Role.MEMBER,
            WorkspaceMembership.Role.VIEWER
        ]:
            raise PermissionDenied("Admins cannot manage other admins.")

        if new_role == WorkspaceMembership.Role.ADMIN:
            raise PermissionDenied("Only the owner can promote members to admin.")

    old_role = target.role

    if old_role == new_role:
        return target

    target.role = new_role
    target.save(update_fields=["role", "updated_at"])

    promoted = (
        new_role == WorkspaceMembership.Role.ADMIN
        or (
            old_role == WorkspaceMembership.Role.VIEWER
            and new_role == WorkspaceMembership.Role.MEMBER
        )
    )

    action = "ROLE_PROMOTED" if promoted else "ROLE_DEMOTED"

    record_audit(
        actor,
        workspace,
        action,
        f"{actor.username} changed {target.user.username}'s role.",
        object_type="WorkspaceMembership",
        object_id=target.id,
        metadata={"old_role": old_role, "new_role": new_role},
        request=request
    )

    return target


# --------------------------------------------------
# REMOVE MEMBER
# --------------------------------------------------

@transaction.atomic
def remove_member(actor, workspace, membership_id, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    actor_membership = require_manager(actor, workspace)
    ensure_workspace_active(workspace)

    target = WorkspaceMembership.objects.select_for_update().filter(
        pk=membership_id,
        workspace=workspace,
        status=WorkspaceMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Active workspace membership not found.")

    if target.role == WorkspaceMembership.Role.OWNER:
        raise PermissionDenied("The workspace owner cannot be removed.")

    if target.user_id == workspace.owner_id:
        raise PermissionDenied("The workspace owner cannot be removed.")

    if target.user_id == actor.id:
        raise ValidationError("Use the leave workspace endpoint instead.")

    if (
        actor_membership.role == WorkspaceMembership.Role.ADMIN
        and target.role not in [
            WorkspaceMembership.Role.MEMBER,
            WorkspaceMembership.Role.VIEWER
        ]
    ):
        raise PermissionDenied("Admins can remove only ordinary members and viewers.")

    target.status = WorkspaceMembership.Status.REMOVED
    target.save(update_fields=["status", "updated_at"])

    record_audit(
        actor,
        workspace,
        "MEMBER_REMOVED",
        f"{actor.username} removed {target.user.username}.",
        object_type="WorkspaceMembership",
        object_id=target.id,
        request=request
    )


# --------------------------------------------------
# LEAVE WORKSPACE
# --------------------------------------------------

@transaction.atomic
def leave_workspace(actor, workspace, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    membership = get_membership(actor, workspace)
    ensure_workspace_active(workspace)

    if membership.role == WorkspaceMembership.Role.OWNER:
        raise ValidationError(
            "Transfer ownership before leaving the workspace."
        )

    membership.status = WorkspaceMembership.Status.LEFT
    membership.save(update_fields=["status", "updated_at"])

    record_audit(
        actor,
        workspace,
        "OTHER",
        f"{actor.username} left the workspace.",
        object_type="WorkspaceMembership",
        object_id=membership.id,
        request=request
    )


# --------------------------------------------------
# TRANSFER OWNERSHIP
# --------------------------------------------------

@transaction.atomic
def transfer_ownership(actor, workspace, target_membership_id, request=None):

    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)

    old_owner_membership = require_owner(actor, workspace)
    ensure_workspace_active(workspace)

    target = WorkspaceMembership.objects.select_for_update().filter(
        pk=target_membership_id,
        workspace=workspace,
        status=WorkspaceMembership.Status.ACTIVE
    ).first()

    if not target:
        raise NotFound("Active target membership not found.")

    if target.user_id == actor.id:
        raise ValidationError("You are already the workspace owner.")

    old_owner_id = actor.id

    # Release the unique active OWNER constraint first.
    old_owner_membership.role = WorkspaceMembership.Role.ADMIN
    old_owner_membership.save(update_fields=["role", "updated_at"])

    target.role = WorkspaceMembership.Role.OWNER
    target.save(update_fields=["role", "updated_at"])

    workspace.owner = target.user
    workspace.save(update_fields=["owner", "updated_at"])

    record_audit(
        actor,
        workspace,
        "OWNERSHIP_TRANSFERRED",
        f"{actor.username} transferred workspace ownership to {target.user.username}.",
        object_type="Workspace",
        object_id=workspace.id,
        metadata={
            "previous_owner_id": old_owner_id,
            "new_owner_id": target.user_id
        },
        request=request
    )

    return workspace