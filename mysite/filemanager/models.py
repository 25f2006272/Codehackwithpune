import os
import uuid

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q


# =====================================================
# FILE STORAGE PATH
# =====================================================

def file_version_upload_path(instance, filename):

    extension = os.path.splitext(filename)[1].lower()

    return (
        f"workspaces/{instance.file_asset.workspace_id}/"
        f"files/{instance.file_asset_id}/"
        f"v{instance.version_number}/"
        f"{uuid.uuid4().hex}{extension}"
    )


# =====================================================
# 1. FOLDER MODEL
# =====================================================

class Folder(models.Model):

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='folders'
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )

    name = models.CharField(
        max_length=150
    )

    description = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_folders'
    )

    is_archived = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'folders'

        ordering = ['name']

        constraints = [

            models.UniqueConstraint(
                fields=['workspace', 'name'],
                condition=Q(parent__isnull=True),
                name='uniq_root_folder_name'
            ),

            models.UniqueConstraint(
                fields=['workspace', 'parent', 'name'],
                condition=Q(parent__isnull=False),
                name='uniq_child_folder_name'
            ),

        ]

        indexes = [

            models.Index(
                fields=['workspace', 'parent'],
                name='folder_ws_parent_idx'
            ),

        ]

    def clean(self):

        if self.parent_id:

            if self.parent.workspace_id != self.workspace_id:

                raise ValidationError(
                    "Parent folder must belong to the same workspace."
                )

            if self.pk and self.parent_id == self.pk:

                raise ValidationError(
                    "A folder cannot be its own parent."
                )

    def __str__(self):

        return self.name


# =====================================================
# 2. FILE ASSET MODEL
# =====================================================

class FileAsset(models.Model):

    class Status(models.TextChoices):

        ACTIVE = 'ACTIVE', 'Active'
        ARCHIVED = 'ARCHIVED', 'Archived'
        TRASHED = 'TRASHED', 'Trashed'

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='files'
    )

    folder = models.ForeignKey(
        Folder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='files'
    )

    name = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_files'
    )

    current_version = models.ForeignKey(
        'filemanager.FileVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'file_assets'

        ordering = ['-created_at']

        constraints = [

            models.UniqueConstraint(
                fields=['workspace', 'name'],
                condition=Q(folder__isnull=True),
                name='uniq_root_file_name'
            ),

            models.UniqueConstraint(
                fields=['workspace', 'folder', 'name'],
                condition=Q(folder__isnull=False),
                name='uniq_folder_file_name'
            ),

        ]

        indexes = [

            models.Index(
                fields=['workspace', 'status'],
                name='file_ws_status_idx'
            ),

        ]

    def clean(self):

        if self.folder_id:

            if self.folder.workspace_id != self.workspace_id:

                raise ValidationError(
                    "File and folder must belong to the same workspace."
                )

        if self.current_version_id:

            if self.current_version.file_asset_id != self.pk:

                raise ValidationError(
                    "Current version must belong to this file."
                )

    def __str__(self):

        return self.name


# =====================================================
# 3. FILE VERSION MODEL
# =====================================================

class FileVersion(models.Model):

    file_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.PositiveIntegerField()

    file = models.FileField(
        upload_to=file_version_upload_path
    )

    original_filename = models.CharField(
        max_length=255
    )

    mime_type = models.CharField(
        max_length=150,
        blank=True
    )

    file_size = models.PositiveBigIntegerField(
        default=0
    )

    checksum = models.CharField(
        max_length=64,
        blank=True
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_file_versions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'file_versions'

        ordering = ['-version_number']

        constraints = [

            models.UniqueConstraint(
                fields=['file_asset', 'version_number'],
                name='uniq_file_version_no'
            ),

        ]

        indexes = [

            models.Index(
                fields=['file_asset', 'version_number'],
                name='version_asset_num_idx'
            ),

        ]

    def __str__(self):

        return f'{self.file_asset.name} - v{self.version_number}'


# =====================================================
# 4. FILE PROJECT LINK MODEL
# =====================================================

class FileProjectLink(models.Model):

    file_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name='project_links'
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='file_links'
    )

    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='linked_project_files'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'file_project_links'

        constraints = [

            models.UniqueConstraint(
                fields=['file_asset', 'project'],
                name='uniq_file_project_link'
            ),

        ]

    def clean(self):

        if self.file_asset.workspace_id != self.project.workspace_id:

            raise ValidationError(
                "File and project must belong to the same workspace."
            )

    def __str__(self):

        return f'{self.file_asset.name} - {self.project.name}'


# =====================================================
# 5. FOLDER PERMISSION MODEL
# =====================================================

class FolderPermission(models.Model):

    class AccessLevel(models.TextChoices):

        VIEW = 'VIEW', 'View'
        UPLOAD = 'UPLOAD', 'Upload'
        EDIT = 'EDIT', 'Edit'
        MANAGE = 'MANAGE', 'Manage'

    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name='permissions'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='folder_permissions'
    )

    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.VIEW
    )

    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_folder_permissions'
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'folder_permissions'

        constraints = [

            models.UniqueConstraint(
                fields=['folder', 'user'],
                name='uniq_folder_user_perm'
            ),

        ]

    def __str__(self):

        return f'{self.user.username} - {self.folder.name} - {self.access_level}'


# =====================================================
# 6. FILE PERMISSION MODEL
# =====================================================

class FilePermission(models.Model):

    class AccessLevel(models.TextChoices):

        VIEW = 'VIEW', 'View'
        DOWNLOAD = 'DOWNLOAD', 'Download'
        EDIT = 'EDIT', 'Edit'
        MANAGE = 'MANAGE', 'Manage'

    file_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name='permissions'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='file_permissions'
    )

    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.VIEW
    )

    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_file_permissions'
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'file_permissions'

        constraints = [

            models.UniqueConstraint(
                fields=['file_asset', 'user'],
                name='uniq_file_user_perm'
            ),

        ]

    def __str__(self):

        return f'{self.user.username} - {self.file_asset.name} - {self.access_level}'