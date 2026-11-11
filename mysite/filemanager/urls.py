from django.urls import path

from .views import (
    WorkspaceFolderListCreateView,
    FolderDetailView,
    FolderMoveView
)
from .file_views import (
    WorkspaceFileListCreateView,
    FileAssetDetailView,
    FileDownloadView,
)

from .version_views import (
    FileVersionHistoryUploadView,
    FileVersionDownloadView,
    FileVersionRestoreView,
)

from .permission_views import (
    FolderPermissionListCreateView,
    FolderPermissionDetailView,
    FilePermissionListCreateView,
    FilePermissionDetailView,
)

urlpatterns = [

    path(
        "workspaces/<int:workspace_id>/folders/",
        WorkspaceFolderListCreateView.as_view(),
        name="workspace-folders"
    ),

    path(
        "folders/<int:folder_id>/",
        FolderDetailView.as_view(),
        name="folder-detail"
    ),

    path(
        "folders/<int:folder_id>/move/",
        FolderMoveView.as_view(),
        name="folder-move"
    ),
    
    path(
        "workspaces/<int:workspace_id>/files/",
        WorkspaceFileListCreateView.as_view(),
        name="workspace-files",
    ),

    path(
        "files/<int:file_id>/",
        FileAssetDetailView.as_view(),
        name="file-detail",
    ),

    path(
        "files/<int:file_id>/download/",
        FileDownloadView.as_view(),
        name="file-download",
    ),

    path(
        "files/<int:file_id>/versions/",
        FileVersionHistoryUploadView.as_view(),
        name="file-version-history",
    ),

    path(
        "files/<int:file_id>/versions/<int:version_id>/download/",
        FileVersionDownloadView.as_view(),
        name="file-version-download",
    ),

    path(
        "files/<int:file_id>/versions/<int:version_id>/restore/",
        FileVersionRestoreView.as_view(),
        name="file-version-restore",
    ),
    
    # Folder permissions

    path(
        "folders/<int:folder_id>/permissions/",
        FolderPermissionListCreateView.as_view(),
        name="folder-permissions",
    ),

    path(
        "folders/<int:folder_id>/permissions/<int:permission_id>/",
        FolderPermissionDetailView.as_view(),
        name="folder-permission-detail",
    ),

    # File permissions

    path(
        "files/<int:file_id>/permissions/",
        FilePermissionListCreateView.as_view(),
        name="file-permissions",
    ),

    path(
        "files/<int:file_id>/permissions/<int:permission_id>/",
        FilePermissionDetailView.as_view(),
        name="file-permission-detail",
    ),
]