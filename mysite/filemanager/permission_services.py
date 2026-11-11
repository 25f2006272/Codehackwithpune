from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
)

from workspaces.models import WorkspaceMembership

from workspaces.services import (
    get_membership,
    ensure_workspace_active,
    record_audit,
)

from .models import (
    Folder,
    FileAsset,
    FolderPermission,
    FilePermission,
)


User = get_user_model()


# =====================================================
# COMMON ACCESS VALIDATION
# =====================================================

def require_workspace_manager(actor, workspace):

    membership = get_membership(actor, workspace)

    ensure_workspace_active(workspace)

    if membership.role not in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN,
    ]:
        raise PermissionDenied(
            "Only workspace owners and admins can manage permissions."
        )

    return membership


def get_active_workspace_user(workspace, user_id):

    try:
        target_user = User.objects.get(
            pk=user_id,
            is_active=True,
        )

    except User.DoesNotExist:
        raise ValidationError({
            "user_id": "User does not exist or is inactive."
        })

    try:
        get_membership(target_user, workspace)

    except PermissionDenied:
        raise ValidationError({
            "user_id": "User must be an active member of this workspace."
        })

    return target_user


def validate_access_level(access_level, permission_model):

    allowed_levels = dict(
        permission_model.AccessLevel.choices
    )

    if access_level not in allowed_levels:
        raise ValidationError({
            "access_level": "Invalid permission level."
        })


# =====================================================
# FOLDER PERMISSIONS
# =====================================================

def list_folder_permissions(actor, folder):

    require_workspace_manager(
        actor,
        folder.workspace,
    )

    if folder.is_archived:
        raise NotFound("Folder not found.")

    return FolderPermission.objects.filter(
        folder=folder,
    ).select_related(
        "user",
        "granted_by",
    ).order_by(
        "user__username"
    )


@transaction.atomic
def grant_folder_permission(
    actor,
    folder,
    user_id,
    access_level,
    request=None,
):

    folder = Folder.objects.select_for_update().select_related(
        "workspace"
    ).get(pk=folder.pk)

    require_workspace_manager(
        actor,
        folder.workspace,
    )

    if folder.is_archived:
        raise ValidationError("Cannot manage permissions of archived folders.")

    validate_access_level(
        access_level,
        FolderPermission,
    )

    target_user = get_active_workspace_user(
        folder.workspace,
        user_id,
    )

    permission, created = FolderPermission.objects.update_or_create(
        folder=folder,
        user=target_user,
        defaults={
            "access_level": access_level,
            "granted_by": actor,
            "is_active": True,
        },
    )

    record_audit(
        actor=actor,
        workspace=folder.workspace,
        action="OTHER",
        description=(
            f"{actor.username} granted {access_level} "
            f"permission on folder {folder.name} "
            f"to {target_user.username}."
        ),
        object_type="FolderPermission",
        object_id=permission.id,
        metadata={
            "event": (
                "FOLDER_PERMISSION_GRANTED"
                if created
                else "FOLDER_PERMISSION_UPDATED"
            ),
            "folder_id": folder.id,
            "user_id": target_user.id,
            "access_level": access_level,
        },
        request=request,
    )

    return permission, created


@transaction.atomic
def update_folder_permission(
    actor,
    folder,
    permission_id,
    access_level,
    request=None,
):

    require_workspace_manager(
        actor,
        folder.workspace,
    )

    validate_access_level(
        access_level,
        FolderPermission,
    )

    try:
        permission = FolderPermission.objects.select_for_update().get(
            id=permission_id,
            folder=folder,
        )

    except FolderPermission.DoesNotExist:
        raise NotFound("Folder permission not found.")

    permission.access_level = access_level
    permission.granted_by = actor
    permission.is_active = True

    permission.save(
        update_fields=[
            "access_level",
            "granted_by",
            "is_active",
            "updated_at",
        ]
    )

    record_audit(
        actor=actor,
        workspace=folder.workspace,
        action="OTHER",
        description=(
            f"Updated folder permission for "
            f"{permission.user.username} on {folder.name}."
        ),
        object_type="FolderPermission",
        object_id=permission.id,
        metadata={
            "event": "FOLDER_PERMISSION_UPDATED",
            "access_level": access_level,
        },
        request=request,
    )

    return permission


@transaction.atomic
def revoke_folder_permission(
    actor,
    folder,
    permission_id,
    request=None,
):

    require_workspace_manager(
        actor,
        folder.workspace,
    )

    try:
        permission = FolderPermission.objects.select_for_update().get(
            id=permission_id,
            folder=folder,
        )

    except FolderPermission.DoesNotExist:
        raise NotFound("Folder permission not found.")

    if not permission.is_active:
        return permission

    permission.is_active = False

    permission.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    record_audit(
        actor=actor,
        workspace=folder.workspace,
        action="OTHER",
        description=(
            f"Revoked folder permission for "
            f"{permission.user.username} on {folder.name}."
        ),
        object_type="FolderPermission",
        object_id=permission.id,
        metadata={
            "event": "FOLDER_PERMISSION_REVOKED",
            "user_id": permission.user_id,
        },
        request=request,
    )

    return permission


# =====================================================
# FILE PERMISSIONS
# =====================================================

def list_file_permissions(actor, file_asset):

    require_workspace_manager(
        actor,
        file_asset.workspace,
    )

    if file_asset.status != FileAsset.Status.ACTIVE:
        raise NotFound("Active file not found.")

    return FilePermission.objects.filter(
        file_asset=file_asset,
    ).select_related(
        "user",
        "granted_by",
    ).order_by(
        "user__username"
    )


@transaction.atomic
def grant_file_permission(
    actor,
    file_asset,
    user_id,
    access_level,
    request=None,
):

    file_asset = FileAsset.objects.select_for_update().select_related(
        "workspace"
    ).get(pk=file_asset.pk)

    require_workspace_manager(
        actor,
        file_asset.workspace,
    )

    if file_asset.status != FileAsset.Status.ACTIVE:
        raise ValidationError("Cannot manage permissions of inactive files.")

    validate_access_level(
        access_level,
        FilePermission,
    )

    target_user = get_active_workspace_user(
        file_asset.workspace,
        user_id,
    )

    permission, created = FilePermission.objects.update_or_create(
        file_asset=file_asset,
        user=target_user,
        defaults={
            "access_level": access_level,
            "granted_by": actor,
            "is_active": True,
        },
    )

    record_audit(
        actor=actor,
        workspace=file_asset.workspace,
        action="OTHER",
        description=(
            f"{actor.username} granted {access_level} "
            f"permission on file {file_asset.name} "
            f"to {target_user.username}."
        ),
        object_type="FilePermission",
        object_id=permission.id,
        metadata={
            "event": (
                "FILE_PERMISSION_GRANTED"
                if created
                else "FILE_PERMISSION_UPDATED"
            ),
            "file_id": file_asset.id,
            "user_id": target_user.id,
            "access_level": access_level,
        },
        request=request,
    )

    return permission, created


@transaction.atomic
def update_file_permission(
    actor,
    file_asset,
    permission_id,
    access_level,
    request=None,
):

    require_workspace_manager(
        actor,
        file_asset.workspace,
    )

    validate_access_level(
        access_level,
        FilePermission,
    )

    try:
        permission = FilePermission.objects.select_for_update().get(
            id=permission_id,
            file_asset=file_asset,
        )

    except FilePermission.DoesNotExist:
        raise NotFound("File permission not found.")

    permission.access_level = access_level
    permission.granted_by = actor
    permission.is_active = True

    permission.save(
        update_fields=[
            "access_level",
            "granted_by",
            "is_active",
            "updated_at",
        ]
    )

    record_audit(
        actor=actor,
        workspace=file_asset.workspace,
        action="OTHER",
        description=(
            f"Updated file permission for "
            f"{permission.user.username} on {file_asset.name}."
        ),
        object_type="FilePermission",
        object_id=permission.id,
        metadata={
            "event": "FILE_PERMISSION_UPDATED",
            "access_level": access_level,
        },
        request=request,
    )

    return permission


@transaction.atomic
def revoke_file_permission(
    actor,
    file_asset,
    permission_id,
    request=None,
):

    require_workspace_manager(
        actor,
        file_asset.workspace,
    )

    try:
        permission = FilePermission.objects.select_for_update().get(
            id=permission_id,
            file_asset=file_asset,
        )

    except FilePermission.DoesNotExist:
        raise NotFound("File permission not found.")

    if not permission.is_active:
        return permission

    permission.is_active = False

    permission.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    record_audit(
        actor=actor,
        workspace=file_asset.workspace,
        action="OTHER",
        description=(
            f"Revoked file permission for "
            f"{permission.user.username} on {file_asset.name}."
        ),
        object_type="FilePermission",
        object_id=permission.id,
        metadata={
            "event": "FILE_PERMISSION_REVOKED",
            "user_id": permission.user_id,
        },
        request=request,
    )

    return permission