from django.http import FileResponse, Http404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from rest_framework.generics import GenericAPIView
from .models import FileAsset

from .file_services import (
    get_file_for_user,
    require_file_access,
)

from .version_services import (
    list_file_versions,
    upload_new_version,
    get_file_version,
    restore_file_version,
)

from .version_serializers import (
    FileVersionUploadSerializer,
    FileVersionReadSerializer,
)


class FileVersionHistoryUploadView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = FileAsset.objects.none()

    serializer_class = FileVersionUploadSerializer

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def get(self, request, file_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        versions = list_file_versions(
            request.user,
            file_asset,
        )

        serializer = FileVersionReadSerializer(
            versions,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request, file_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        serializer = FileVersionUploadSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        version = upload_new_version(
            actor=request.user,
            file_asset=file_asset,
            uploaded_file=serializer.validated_data["file"],
            request=request,
        )

        response_serializer = FileVersionReadSerializer(
            version,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class FileVersionDownloadView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id, version_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        version = get_file_version(
            request.user,
            file_asset,
            version_id,
        )

        require_file_access(
            request.user,
            file_asset,
            "DOWNLOAD",
        )

        if not version.file:
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


class FileVersionRestoreView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, file_id, version_id):

        file_asset = get_file_for_user(
            request.user,
            file_id,
        )

        version = restore_file_version(
            actor=request.user,
            file_asset=file_asset,
            version_id=version_id,
            request=request,
        )

        serializer = FileVersionReadSerializer(
            version,
        )

        return Response({
            "message": "File version restored successfully.",
            "current_version": serializer.data,
        })
        