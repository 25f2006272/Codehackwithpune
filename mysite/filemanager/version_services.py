import hashlib
import mimetypes

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from rest_framework.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
)

from .models import FileAsset, FileVersion
from .file_services import (
    MAX_FILE_SIZE,
    require_file_access,
    sanitize_filename,
)


def calculate_version_checksum(uploaded_file):
    digest = hashlib.sha256()

    for chunk in uploaded_file.chunks():
        digest.update(chunk)

    uploaded_file.seek(0)

    return digest.hexdigest()


def list_file_versions(user, file_asset):

    require_file_access(user, file_asset, "VIEW")

    return FileVersion.objects.filter(
        file_asset=file_asset
    ).select_related(
        "uploaded_by"
    ).order_by("-version_number")


def upload_new_version(actor, file_asset, uploaded_file, request=None):

    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError({
            "file": "Maximum allowed file size is 50 MB."
        })

    filename = sanitize_filename(uploaded_file.name)

    mime_type = (
        uploaded_file.content_type
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    checksum = calculate_version_checksum(uploaded_file)

    version = None

    try:
        with transaction.atomic():

            locked_asset = FileAsset.objects.select_for_update().get(
                id=file_asset.id,
                status="ACTIVE",
            )

            require_file_access(
                actor,
                locked_asset,
                "EDIT",
            )

            latest_version = FileVersion.objects.filter(
                file_asset=locked_asset
            ).aggregate(
                max_version=Max("version_number")
            )["max_version"]

            next_version_number = (latest_version or 0) + 1

            version = FileVersion(
                file_asset=locked_asset,
                version_number=next_version_number,
                file=uploaded_file,
                original_filename=filename,
                mime_type=mime_type,
                file_size=uploaded_file.size,
                checksum=checksum,
                uploaded_by=actor,
            )

            version.save()

            locked_asset.current_version = version

            locked_asset.save(
                update_fields=[
                    "current_version",
                    "updated_at",
                ]
            )

            from workspaces.services import record_audit

            record_audit(
                actor=actor,
                workspace=locked_asset.workspace,
                action="OTHER",
                description=(
                    f"Uploaded version {next_version_number} "
                    f"of file {locked_asset.name}."
                ),
                object_type="FileAsset",
                object_id=locked_asset.id,
                metadata={
                    "event": "FILE_VERSION_UPLOADED",
                    "filename": locked_asset.name,
                    "original_filename": filename,
                    "version": next_version_number,
                },
                request=request,
            )

            return version

    except Exception:

        # Remove the physical file if the database operation fails.
        if version and version.file.name:
            version.file.storage.delete(version.file.name)

        raise


def get_file_version(user, file_asset, version_id):

    require_file_access(
        user,
        file_asset,
        "VIEW",
    )

    try:
        return FileVersion.objects.get(
            id=version_id,
            file_asset=file_asset,
        )

    except FileVersion.DoesNotExist:
        raise NotFound("File version not found.")


def restore_file_version(actor, file_asset, version_id, request=None):

    with transaction.atomic():

        locked_asset = FileAsset.objects.select_for_update().get(
            id=file_asset.id,
            status="ACTIVE",
        )

        require_file_access(
            actor,
            locked_asset,
            "EDIT",
        )

        try:
            version = FileVersion.objects.get(
                id=version_id,
                file_asset=locked_asset,
            )

        except FileVersion.DoesNotExist:
            raise NotFound("File version not found.")

        old_version_number = (
            locked_asset.current_version.version_number
            if locked_asset.current_version
            else None
        )

        locked_asset.current_version = version

        locked_asset.save(
            update_fields=[
                "current_version",
                "updated_at",
            ]
        )

        from workspaces.services import record_audit

        record_audit(
            actor=actor,
            workspace=locked_asset.workspace,
            action="OTHER",
            description=(
                f"Restored file {locked_asset.name} "
                f"to version {version.version_number}."
            ),
            object_type="FileAsset",
            object_id=locked_asset.id,
            metadata={
                "event": "FILE_VERSION_RESTORED",
                "previous_version": old_version_number,
                "restored_version": version.version_number,
            },
            request=request,
        )

        return version