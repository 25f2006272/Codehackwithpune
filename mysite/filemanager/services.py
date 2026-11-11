from django.db import transaction, IntegrityError

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
    ensure_workspace_active,
    record_audit
)

from .models import (
    Folder,
    FileAsset,
    FolderPermission
)


ACCESS_RANK = {
    "VIEW": 1,
    "UPLOAD": 2,
    "EDIT": 3,
    "MANAGE": 4
}


# ==========================================
# FOLDER ACCESS CONTROL
# ==========================================

def get_folder_access(user, folder):

    workspace_membership = get_membership(
        user,
        folder.workspace
    )

    ensure_workspace_active(folder.workspace)

    if workspace_membership.role in [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN
    ]:
        return "MANAGE"

    current = folder

    # Nearest explicit permission takes precedence,
    # including for workspace-level VIEWER users.
    while current:

        permission = FolderPermission.objects.filter(
            folder=current,
            user=user,
            is_active=True
        ).first()

        if permission:
            return permission.access_level

        current = current.parent

    if workspace_membership.role == WorkspaceMembership.Role.VIEWER:
        return "VIEW"

    return "EDIT"


def require_folder_access(user, folder, required_level):

    actual_level = get_folder_access(user, folder)

    if ACCESS_RANK[actual_level] < ACCESS_RANK[required_level]:

        raise PermissionDenied(
            f"You need {required_level} access to perform this action."
        )

    return actual_level


def validate_folder_parent(workspace, parent):

    if parent is None:
        return

    if parent.workspace_id != workspace.id:
        raise ValidationError(
            "Parent folder must belong to the same workspace."
        )

    if parent.is_archived:
        raise ValidationError(
            "Cannot use an archived folder."
        )


# ==========================================
# CREATE FOLDER
# ==========================================

@transaction.atomic
def create_folder(actor, workspace, data, request=None):

    # Lock workspace during folder creation.
    workspace = Workspace.objects.select_for_update().get(
        pk=workspace.pk
    )

    # Verify active workspace membership.
    membership = get_membership(actor, workspace)

    # Prevent folder creation in archived workspaces.
    ensure_workspace_active(workspace)

    # --------------------------------------------
    # GET AND VALIDATE PARENT FOLDER
    # --------------------------------------------

    parent_id = data.get("parent_id")

    parent = None

    if parent_id is not None:

        parent = Folder.objects.select_for_update().filter(
            pk=parent_id,
            workspace=workspace,
            is_archived=False
        ).first()

        if not parent:
            raise NotFound("Parent folder not found.")

        # Validate that parent belongs to the workspace.
        validate_folder_parent(workspace, parent)

        # User must have EDIT or MANAGE permission
        # on the parent folder.
        require_folder_access(
            actor,
            parent,
            "EDIT"
        )

    else:

        # Workspace VIEWER cannot create root folders.
        # However, explicitly granted EDIT permission
        # on an existing folder allows child creation.
        if membership.role == WorkspaceMembership.Role.VIEWER:

            raise PermissionDenied(
                "Workspace viewers cannot create root folders."
            )

    # --------------------------------------------
    # VALIDATE FOLDER NAME
    # --------------------------------------------

    name = data.get("name", "").strip()

    if not name:
        raise ValidationError(
            "Folder name is required."
        )

    if len(name) > 150:
        raise ValidationError(
            "Folder name cannot exceed 150 characters."
        )

    description = data.get("description", "")

    # --------------------------------------------
    # CREATE FOLDER
    # --------------------------------------------

    try:

        with transaction.atomic():

            folder = Folder.objects.create(
                workspace=workspace,
                parent=parent,
                name=name,
                description=description,
                created_by=actor
            )

    except IntegrityError as exc:

        raise ValidationError(
            "A folder with this name already exists at this location."
        ) from exc

    # --------------------------------------------
    # RECORD AUDIT LOG
    # --------------------------------------------

    record_audit(
        actor=actor,
        workspace=workspace,
        action="OTHER",
        description=(
            f"{actor.username} created folder {folder.name}."
        ),
        object_type="Folder",
        object_id=folder.id,
        metadata={
            "event": "FOLDER_CREATED",
            "parent_id": parent.id if parent else None,
            "folder_name": folder.name
        },
        request=request
    )

    return folder


# ==========================================
# LIST FOLDERS
# ==========================================

def list_workspace_folders(user, workspace, parent_id=None, search=None):

    get_membership(user, workspace)

    ensure_workspace_active(workspace)

    parent = None

    if parent_id is not None:

        parent = Folder.objects.filter(
            pk=parent_id,
            workspace=workspace,
            is_archived=False
        ).first()

        if not parent:
            raise NotFound("Parent folder not found.")

        require_folder_access(user, parent, "VIEW")

    queryset = Folder.objects.filter(
        workspace=workspace,
        parent=parent,
        is_archived=False
    )

    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset.select_related(
        "workspace",
        "parent",
        "created_by"
    )


# ==========================================
# GET FOLDER
# ==========================================

def get_folder_for_user(user, folder_id):

    folder = Folder.objects.select_related(
        "workspace",
        "parent",
        "created_by"
    ).filter(
        pk=folder_id,
        is_archived=False
    ).first()

    if not folder:
        raise NotFound("Folder not found.")

    require_folder_access(
        user,
        folder,
        "VIEW"
    )

    return folder


# ==========================================
# UPDATE FOLDER
# ==========================================

@transaction.atomic
def update_folder(actor, folder, data, request=None):

    folder = Folder.objects.select_for_update().get(
        pk=folder.pk
    )

    require_folder_access(
        actor,
        folder,
        "EDIT"
    )

    ensure_workspace_active(folder.workspace)

    if folder.is_archived:
        raise ValidationError(
            "Archived folders cannot be modified."
        )

    for field, value in data.items():

        if field == "name":
            value = value.strip()

            if not value:
                raise ValidationError(
                    "Folder name cannot be empty."
                )

        setattr(folder, field, value)

    try:
        with transaction.atomic():
            folder.save()

    except IntegrityError as exc:

        raise ValidationError(
            "A folder with this name already exists."
        ) from exc

    record_audit(
        actor,
        folder.workspace,
        "OTHER",
        f"{actor.username} updated folder {folder.name}.",
        object_type="Folder",
        object_id=folder.id,
        metadata={
            "event": "FOLDER_UPDATED",
            "updated_fields": list(data.keys())
        },
        request=request
    )

    return folder


# ==========================================
# MOVE FOLDER
# ==========================================

@transaction.atomic
def move_folder(actor, folder, new_parent_id, request=None):

    folder = Folder.objects.select_for_update().get(
        pk=folder.pk
    )

    require_folder_access(
        actor,
        folder,
        "MANAGE"
    )

    ensure_workspace_active(folder.workspace)

    if folder.is_archived:
        raise ValidationError(
            "Archived folders cannot be moved."
        )

    new_parent = None

    if new_parent_id is not None:

        new_parent = Folder.objects.filter(
            pk=new_parent_id,
            workspace=folder.workspace,
            is_archived=False
        ).first()

        if not new_parent:
            raise NotFound(
                "Destination folder not found."
            )

        require_folder_access(
            actor,
            new_parent,
            "EDIT"
        )

        # Prevent moving a folder inside itself or its descendants.
        current = new_parent

        while current:

            if current.pk == folder.pk:
                raise ValidationError(
                    "A folder cannot be moved inside itself or its descendants."
                )

            current = current.parent

    old_parent_id = folder.parent_id

    folder.parent = new_parent

    try:
        with transaction.atomic():
            folder.save(update_fields=["parent", "updated_at"])

    except IntegrityError as exc:

        raise ValidationError(
            "A folder with this name already exists at the destination."
        ) from exc

    record_audit(
        actor,
        folder.workspace,
        "OTHER",
        f"{actor.username} moved folder {folder.name}.",
        object_type="Folder",
        object_id=folder.id,
        metadata={
            "event": "FOLDER_MOVED",
            "old_parent_id": old_parent_id,
            "new_parent_id": new_parent_id
        },
        request=request
    )

    return folder


# ==========================================
# ARCHIVE FOLDER
# ==========================================

@transaction.atomic
def archive_folder(actor, folder, request=None):

    folder = Folder.objects.select_for_update().get(
        pk=folder.pk
    )

    require_folder_access(
        actor,
        folder,
        "MANAGE"
    )

    ensure_workspace_active(folder.workspace)

    if folder.is_archived:
        raise ValidationError(
            "Folder is already archived."
        )

    # Collect all descendants.
    folder_ids = [folder.id]
    pending_ids = [folder.id]

    while pending_ids:

        children = list(
            Folder.objects.filter(
                parent_id__in=pending_ids,
                workspace=folder.workspace,
                is_archived=False
            ).values_list("id", flat=True)
        )

        folder_ids.extend(children)
        pending_ids = children

    # Archive folders without deleting them.
    Folder.objects.filter(
        id__in=folder_ids
    ).update(is_archived=True)

    # Archive files stored inside the folder tree.
    FileAsset.objects.filter(
        folder_id__in=folder_ids,
        status=FileAsset.Status.ACTIVE
    ).update(
        status=FileAsset.Status.ARCHIVED
    )

    record_audit(
        actor,
        folder.workspace,
        "OTHER",
        f"{actor.username} archived folder {folder.name}.",
        object_type="Folder",
        object_id=folder.id,
        metadata={
            "event": "FOLDER_ARCHIVED",
            "archived_folder_ids": folder_ids
        },
        request=request
    )