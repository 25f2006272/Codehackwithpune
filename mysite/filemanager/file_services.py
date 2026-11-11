import hashlib
import mimetypes

from django.db import transaction, IntegrityError
from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
)

from workspaces.services import (
    get_membership,
    ensure_workspace_active,
    record_audit,
)

from .models import FileAsset, FileVersion, FilePermission, Folder
from .services import get_folder_access, require_folder_access


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

FILE_ACCESS_RANK = {
    "VIEW": 1,
    "DOWNLOAD": 2,
    "EDIT": 3,
    "MANAGE": 4,
}


def get_workspace_file_rank(user, workspace):
    membership = get_membership(user, workspace)
    ensure_workspace_active(workspace)

    if membership.role in ["OWNER", "ADMIN"]:
        return 4

    if membership.role == "VIEWER":
        return 1

    return 3


def get_file_access_rank(user, file_asset):
    workspace = file_asset.workspace

    membership = get_membership(user, workspace)
    ensure_workspace_active(workspace)

    # Workspace Owner and Admin have full access.
    if membership.role in ["OWNER", "ADMIN"]:
        return 4

    # Direct file permission overrides inherited folder permission.
    permission = FilePermission.objects.filter(
        file_asset=file_asset,
        user=user,
        is_active=True,
    ).first()

    if permission:
        return FILE_ACCESS_RANK.get(permission.access_level, 0)

    # Inherit permissions from the containing folder.
    if file_asset.folder_id:
        folder_access = get_folder_access(user, file_asset.folder)

        folder_to_file_rank = {
            "VIEW": 1,
            "UPLOAD": 1,
            "EDIT": 3,
            "MANAGE": 4,
        }

        return folder_to_file_rank[folder_access]

    # Root-level file: use workspace membership.
    return get_workspace_file_rank(user, workspace)


def require_file_access(user, file_asset, required_access):
    current_rank = get_file_access_rank(user, file_asset)
    required_rank = FILE_ACCESS_RANK[required_access]

    if current_rank < required_rank:
        raise PermissionDenied(
            f"You do not have {required_access} access to this file."
        )


def get_file_for_user(user, file_id):
    try:
        file_asset = FileAsset.objects.select_related(
            "workspace",
            "folder",
            "created_by",
            "current_version",
        ).get(
            id=file_id,
            status="ACTIVE",
        )
    except FileAsset.DoesNotExist:
        raise NotFound("File not found.")

    require_file_access(user, file_asset, "VIEW")

    return file_asset


def list_workspace_files(user, workspace, folder=None, search=None):
    get_membership(user, workspace)
    ensure_workspace_active(workspace)

    if folder:
        if folder.workspace_id != workspace.id or folder.is_archived:
            raise NotFound("Folder not found.")

        require_folder_access(user, folder, "VIEW")
        queryset = FileAsset.objects.filter(folder=folder)
    else:
        queryset = FileAsset.objects.filter(
            folder__isnull=True,
        )

    queryset = queryset.filter(
        workspace=workspace,
        status="ACTIVE",
    ).select_related(
        "folder",
        "created_by",
        "current_version",
    ).order_by("-created_at")

    if search:
        queryset = queryset.filter(name__icontains=search)

    # Only return files for which the current user has VIEW access.
    visible_files = []

    for file_asset in queryset:
        try:
            require_file_access(user, file_asset, "VIEW")
            visible_files.append(file_asset)
        except PermissionDenied:
            continue

    return visible_files


def calculate_checksum(uploaded_file):
    digest = hashlib.sha256()

    for chunk in uploaded_file.chunks():
        digest.update(chunk)

    uploaded_file.seek(0)

    return digest.hexdigest()


def sanitize_filename(filename):
    filename = str(filename).replace("\\", "/").split("/")[-1].strip()

    if not filename or filename in [".", ".."] or "\x00" in filename:
        raise ValidationError({"file": "Invalid filename."})

    if len(filename) > 255:
        raise ValidationError({
            "file": "Filename cannot exceed 255 characters."
        })

    return filename


def upload_file(actor, workspace, uploaded_file, folder=None,
                description="", request=None):

    membership = get_membership(actor, workspace)
    ensure_workspace_active(workspace)

    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError({
            "file": "Maximum allowed file size is 50 MB."
        })

    if folder:
        if folder.workspace_id != workspace.id or folder.is_archived:
            raise ValidationError({
                "folder_id": "Invalid folder for this workspace."
            })

        require_folder_access(actor, folder, "UPLOAD")
    else:
        if get_workspace_file_rank(actor, workspace) < 2:
            raise PermissionDenied(
                "You do not have permission to upload files."
            )

    original_filename = sanitize_filename(uploaded_file.name)

    mime_type = (
        uploaded_file.content_type
        or mimetypes.guess_type(original_filename)[0]
        or "application/octet-stream"
    )

    checksum = calculate_checksum(uploaded_file)

    version = None

    try:
        with transaction.atomic():
            file_asset = FileAsset.objects.create(
                workspace=workspace,
                folder=folder,
                name=original_filename,
                description=description,
                created_by=actor,
                status="ACTIVE",
            )

            version = FileVersion(
                file_asset=file_asset,
                version_number=1,
                file=uploaded_file,
                original_filename=original_filename,
                mime_type=mime_type,
                file_size=uploaded_file.size,
                checksum=checksum,
                uploaded_by=actor,
            )
            version.save()

            file_asset.current_version = version
            file_asset.save(
                update_fields=["current_version", "updated_at"]
            )

            record_audit(
                actor=actor,
                workspace=workspace,
                action="OTHER",
                description=f"Uploaded file: {original_filename}",
                object_type="FileAsset",
                object_id=file_asset.id,
                metadata={
                    "event": "FILE_UPLOADED",
                    "filename": original_filename,
                    "version": 1,
                },
                request=request,
            )

            return file_asset

    except IntegrityError:
        if version and version.file.name:
            version.file.storage.delete(version.file.name)

        raise ValidationError({
            "file": (
                "A file with this name already exists in this location. "
                "Use a different filename."
            )
        })

    except Exception:
        if version and version.file.name:
            version.file.storage.delete(version.file.name)

        raise