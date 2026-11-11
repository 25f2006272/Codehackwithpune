from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from workspaces.models import Workspace

from .models import Folder, FileAsset
from . import services

from .serializers import (
    FolderCreateSerializer,
    FolderUpdateSerializer,
    FolderReadSerializer,
    FolderMoveSerializer
)


class WorkspaceFolderListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/v1/workspaces/<workspace_id>/folders/

    def get(self, request, workspace_id):

        workspace = get_object_or_404(
            Workspace,
            pk=workspace_id
        )

        parent_id = request.query_params.get("parent_id")

        if parent_id in [None, ""]:
            parent_id = None
        else:
            try:
                parent_id = int(parent_id)
            except ValueError:
                return Response(
                    {"detail": "Invalid parent_id."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        folders = services.list_workspace_folders(
            request.user,
            workspace,
            parent_id=parent_id,
            search=request.query_params.get("search")
        )

        folders = folders.annotate(
            subfolder_count=Count(
                "subfolders",
                filter=Q(subfolders__is_archived=False),
                distinct=True
            ),
            file_count=Count(
                "files",
                filter=Q(files__status=FileAsset.Status.ACTIVE),
                distinct=True
            )
        )

        serializer = FolderReadSerializer(
            folders,
            many=True
        )

        return Response(serializer.data)

    # POST /api/v1/workspaces/<workspace_id>/folders/

    def post(self, request, workspace_id):

        workspace = get_object_or_404(
            Workspace,
            pk=workspace_id
        )

        serializer = FolderCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        folder = services.create_folder(
            request.user,
            workspace,
            serializer.validated_data,
            request=request
        )

        return Response(
            FolderReadSerializer(folder).data,
            status=status.HTTP_201_CREATED
        )


class FolderDetailView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/v1/folders/<folder_id>/

    def get(self, request, folder_id):

        folder = services.get_folder_for_user(
            request.user,
            folder_id
        )

        return Response(
            FolderReadSerializer(folder).data
        )

    # PATCH /api/v1/folders/<folder_id>/

    def patch(self, request, folder_id):

        folder = services.get_folder_for_user(
            request.user,
            folder_id
        )

        serializer = FolderUpdateSerializer(
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        folder = services.update_folder(
            request.user,
            folder,
            serializer.validated_data,
            request=request
        )

        return Response(
            FolderReadSerializer(folder).data
        )

    # DELETE /api/v1/folders/<folder_id>/
    # Soft archive, not permanent deletion.

    def delete(self, request, folder_id):

        folder = services.get_folder_for_user(
            request.user,
            folder_id
        )

        services.archive_folder(
            request.user,
            folder,
            request=request
        )

        return Response(
            {"detail": "Folder archived successfully."},
            status=status.HTTP_200_OK
        )


class FolderMoveView(APIView):

    permission_classes = [IsAuthenticated]

    # POST /api/v1/folders/<folder_id>/move/

    def post(self, request, folder_id):

        folder = services.get_folder_for_user(
            request.user,
            folder_id
        )

        serializer = FolderMoveSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        folder = services.move_folder(
            request.user,
            folder,
            serializer.validated_data["parent_id"],
            request=request
        )

        return Response(
            FolderReadSerializer(folder).data,
            status=status.HTTP_200_OK
        )
