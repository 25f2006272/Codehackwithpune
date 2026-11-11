from django.shortcuts import get_object_or_404

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from filemanager.models import FileVersion
from filemanager.file_services import get_file_for_user

from .models import DocumentExtraction

from .services import extract_file_version

from .serializers import (
    ExtractionRequestSerializer,
    DocumentExtractionReadSerializer,
    DocumentChunkReadSerializer,
)


class DocumentExtractionView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = ExtractionRequestSerializer

    queryset = DocumentExtraction.objects.none()

    def get_file_asset(self, request, file_id):

        return get_file_for_user(
            request.user,
            file_id
        )

    def get(self, request, file_id):

        file_asset = self.get_file_asset(
            request,
            file_id
        )

        if not file_asset.current_version:

            raise ValidationError(
                "This file has no current version."
            )

        extraction = get_object_or_404(
            DocumentExtraction.objects.filter(
                file_version=file_asset.current_version
            ).order_by("-extraction_version"),
        )

        serializer = DocumentExtractionReadSerializer(
            extraction
        )

        return Response(serializer.data)

    def post(self, request, file_id):

        file_asset = self.get_file_asset(
            request,
            file_id
        )

        if not file_asset.current_version:

            raise ValidationError(
                "This file has no current version."
            )

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        extraction, created = extract_file_version(
            file_version=file_asset.current_version,
            actor=request.user,
            force=serializer.validated_data["force"],
            request=request,
        )

        response_serializer = DocumentExtractionReadSerializer(
            extraction
        )

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            )
        )


class DocumentChunkListView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = DocumentExtraction.objects.none()

    serializer_class = DocumentChunkReadSerializer

    def get(self, request, extraction_id):

        extraction = get_object_or_404(
            DocumentExtraction.objects.select_related(
                "file_version__file_asset"
            ),
            id=extraction_id,
            status=DocumentExtraction.Status.COMPLETED,
        )

        # Verify that the requester can access the source file.
        get_file_for_user(
            request.user,
            extraction.file_version.file_asset_id,
        )

        chunks = extraction.chunks.all()

        serializer = DocumentChunkReadSerializer(
            chunks,
            many=True
        )

        return Response(serializer.data)