from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, FormParser


from workspaces.models import Workspace

from .models import Folder, FileAsset
from .file_services import (
    upload_file,
    list_workspace_files,
    get_file_for_user,
    require_file_access,
)
from .file_serializers import (
    FileUploadSerializer,
    FileAssetReadSerializer,
)


class WorkspaceFileListCreateView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = FileAsset.objects.none()

    serializer_class = FileUploadSerializer

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def get(self, request, workspace_id):

        workspace = get_object_or_404(
            Workspace,
            id=workspace_id,
        )

        folder = None
        folder_id = request.query_params.get("folder_id")

        if folder_id:
            try:
                folder_id = int(folder_id)
            except ValueError:
                raise ValidationError({
                    "folder_id": "Invalid folder ID."
                })

            folder = get_object_or_404(
                Folder,
                id=folder_id,
                workspace=workspace,
                is_archived=False,
            )

        search = request.query_params.get("search")

        files = list_workspace_files(
            user=request.user,
            workspace=workspace,
            folder=folder,
            search=search,
        )

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(files, request)

        serializer = FileAssetReadSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    def post(self, request, workspace_id):

        workspace = get_object_or_404(
            Workspace,
            id=workspace_id,
        )

        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        folder_id = serializer.validated_data.get("folder_id")
        description = serializer.validated_data.get("description", "")

        folder = None

        if folder_id is not None:
            folder = get_object_or_404(
                Folder,
                id=folder_id,
                workspace=workspace,
                is_archived=False,
            )

        file_asset = upload_file(
            actor=request.user,
            workspace=workspace,
            uploaded_file=uploaded_file,
            folder=folder,
            description=description,
            request=request,
        )

        response_serializer = FileAssetReadSerializer(file_asset)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class FileAssetDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        serializer = FileAssetReadSerializer(file_asset)

        return Response(serializer.data)


class FileDownloadView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        require_file_access(
            request.user,
            file_asset,
            "DOWNLOAD",
        )

        version = file_asset.current_version

        if not version or not version.file:
            raise Http404("File content not found.")

        try:
            file_handle = version.file.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404("File content is not available.")

        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=version.original_filename or file_asset.name,
            content_type=version.mime_type or "application/octet-stream",
        )