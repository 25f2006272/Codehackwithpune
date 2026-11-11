from django.shortcuts import get_object_or_404

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Folder,
    FileAsset,
    FolderPermission,
    FilePermission,
)

from .permission_services import (
    list_folder_permissions,
    grant_folder_permission,
    update_folder_permission,
    revoke_folder_permission,

    list_file_permissions,
    grant_file_permission,
    update_file_permission,
    revoke_file_permission,
)

from .permission_serializers import (
    FolderPermissionGrantSerializer,
    FilePermissionGrantSerializer,
    PermissionUpdateSerializer,
    FolderPermissionReadSerializer,
    FilePermissionReadSerializer,
)


# =====================================================
# FOLDER PERMISSION LIST AND CREATE
# =====================================================

class FolderPermissionListCreateView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = Folder.objects.none()

    serializer_class = FolderPermissionGrantSerializer

    def get(self, request, folder_id):

        folder = get_object_or_404(
            Folder.objects.select_related("workspace"),
            id=folder_id
        )

        permissions = list_folder_permissions(
            request.user,
            folder
        )

        serializer = FolderPermissionReadSerializer(
            permissions,
            many=True
        )

        return Response(serializer.data)

    def post(self, request, folder_id):

        folder = get_object_or_404(
            Folder.objects.select_related("workspace"),
            id=folder_id
        )

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        permission, created = grant_folder_permission(
            actor=request.user,
            folder=folder,
            user_id=serializer.validated_data["user_id"],
            access_level=serializer.validated_data["access_level"],
            request=request
        )

        response_serializer = FolderPermissionReadSerializer(
            permission
        )

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            )
        )


# =====================================================
# FOLDER PERMISSION UPDATE AND REVOKE
# =====================================================

class FolderPermissionDetailView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = FolderPermission.objects.none()

    serializer_class = PermissionUpdateSerializer

    def patch(self, request, folder_id, permission_id):

        folder = get_object_or_404(
            Folder.objects.select_related("workspace"),
            id=folder_id
        )

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        permission = update_folder_permission(
            actor=request.user,
            folder=folder,
            permission_id=permission_id,
            access_level=serializer.validated_data["access_level"],
            request=request
        )

        response_serializer = FolderPermissionReadSerializer(
            permission
        )

        return Response(response_serializer.data)

    def delete(self, request, folder_id, permission_id):

        folder = get_object_or_404(
            Folder.objects.select_related("workspace"),
            id=folder_id
        )

        permission = revoke_folder_permission(
            actor=request.user,
            folder=folder,
            permission_id=permission_id,
            request=request
        )

        return Response({
            "message": "Folder permission revoked successfully.",
            "permission_id": permission.id,
            "is_active": permission.is_active
        })


# =====================================================
# FILE PERMISSION LIST AND CREATE
# =====================================================

class FilePermissionListCreateView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = FileAsset.objects.none()

    serializer_class = FilePermissionGrantSerializer

    def get(self, request, file_id):

        file_asset = get_object_or_404(
            FileAsset.objects.select_related("workspace"),
            id=file_id
        )

        permissions = list_file_permissions(
            request.user,
            file_asset
        )

        serializer = FilePermissionReadSerializer(
            permissions,
            many=True
        )

        return Response(serializer.data)

    def post(self, request, file_id):

        file_asset = get_object_or_404(
            FileAsset.objects.select_related("workspace"),
            id=file_id
        )

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        permission, created = grant_file_permission(
            actor=request.user,
            file_asset=file_asset,
            user_id=serializer.validated_data["user_id"],
            access_level=serializer.validated_data["access_level"],
            request=request
        )

        response_serializer = FilePermissionReadSerializer(
            permission
        )

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            )
        )


# =====================================================
# FILE PERMISSION UPDATE AND REVOKE
# =====================================================

class FilePermissionDetailView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = FilePermission.objects.none()

    serializer_class = PermissionUpdateSerializer

    def patch(self, request, file_id, permission_id):

        file_asset = get_object_or_404(
            FileAsset.objects.select_related("workspace"),
            id=file_id
        )

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        permission = update_file_permission(
            actor=request.user,
            file_asset=file_asset,
            permission_id=permission_id,
            access_level=serializer.validated_data["access_level"],
            request=request
        )

        response_serializer = FilePermissionReadSerializer(
            permission
        )

        return Response(response_serializer.data)

    def delete(self, request, file_id, permission_id):

        file_asset = get_object_or_404(
            FileAsset.objects.select_related("workspace"),
            id=file_id
        )

        permission = revoke_file_permission(
            actor=request.user,
            file_asset=file_asset,
            permission_id=permission_id,
            request=request
        )

        return Response({
            "message": "File permission revoked successfully.",
            "permission_id": permission.id,
            "is_active": permission.is_active
        })