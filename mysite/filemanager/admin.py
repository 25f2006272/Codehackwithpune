from django.contrib import admin

from .models import (
    Folder,
    FileAsset,
    FileVersion,
    FileProjectLink,
    FolderPermission,
    FilePermission,
)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'workspace',
        'parent',
        'created_by',
        'is_archived',
        'created_at',
    )

    list_filter = (
        'is_archived',
        'created_at',
    )

    search_fields = (
        'name',
        'workspace__name',
    )


@admin.register(FileAsset)
class FileAssetAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'workspace',
        'folder',
        'status',
        'created_by',
        'updated_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'name',
        'workspace__name',
    )


@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):

    list_display = (
        'file_asset',
        'version_number',
        'original_filename',
        'mime_type',
        'file_size',
        'uploaded_by',
        'created_at',
    )

    search_fields = (
        'file_asset__name',
        'original_filename',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(FileProjectLink)
class FileProjectLinkAdmin(admin.ModelAdmin):

    list_display = (
        'file_asset',
        'project',
        'linked_by',
        'created_at',
    )

    search_fields = (
        'file_asset__name',
        'project__name',
    )


@admin.register(FolderPermission)
class FolderPermissionAdmin(admin.ModelAdmin):

    list_display = (
        'folder',
        'user',
        'access_level',
        'is_active',
    )

    list_filter = (
        'access_level',
        'is_active',
    )


@admin.register(FilePermission)
class FilePermissionAdmin(admin.ModelAdmin):

    list_display = (
        'file_asset',
        'user',
        'access_level',
        'is_active',
    )

    list_filter = (
        'access_level',
        'is_active',
    )