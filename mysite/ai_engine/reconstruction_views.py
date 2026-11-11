from django.shortcuts import get_object_or_404

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from projects.models import Project

from .models import (
    AnalysisRun,
    KnowledgeItem,
)

from .reconstruction import (
    require_project_access,
    run_project_reconstruction,
)

from .reconstruction_serializers import (
    AnalysisRequestSerializer,
    AnalysisRunReadSerializer,
    KnowledgeItemReadSerializer,
)


class ProjectAnalysisView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = Project.objects.none()

    serializer_class = AnalysisRequestSerializer

    def post(self, request, project_id):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        analysis_run, items, conflicts = (
            run_project_reconstruction(
                actor=request.user,
                project_id=project_id,
                file_ids=serializer.validated_data["file_ids"],
            )
        )

        response_serializer = AnalysisRunReadSerializer(
            analysis_run
        )

        return Response(
            {
                "analysis_run": response_serializer.data,
                "knowledge_items": KnowledgeItemReadSerializer(
                    items,
                    many=True
                ).data,
                "conflicts_created": len(conflicts),
            },
            status=status.HTTP_201_CREATED
        )


class ProjectKnowledgeListView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = KnowledgeItem.objects.none()

    serializer_class = KnowledgeItemReadSerializer

    def get(self, request, project_id):

        project = get_object_or_404(
            Project.objects.select_related("workspace"),
            id=project_id
        )

        require_project_access(
            request.user,
            project,
            for_analysis=False
        )

        items = KnowledgeItem.objects.filter(
            project=project
        ).select_related(
            "assigned_to",
            "analysis_run",
        ).prefetch_related(
            "evidence__document_chunk__extraction__file_version"
        )

        serializer = self.get_serializer(
            items,
            many=True
        )

        return Response(serializer.data)


class ProjectAnalysisRunListView(GenericAPIView):

    permission_classes = [IsAuthenticated]

    queryset = AnalysisRun.objects.none()

    serializer_class = AnalysisRunReadSerializer

    def get(self, request, project_id):

        project = get_object_or_404(
            Project.objects.select_related("workspace"),
            id=project_id
        )

        require_project_access(
            request.user,
            project,
            for_analysis=False
        )

        runs = AnalysisRun.objects.filter(
            project=project
        ).select_related(
            "project"
        ).order_by(
            "-created_at"
        )

        serializer = self.get_serializer(
            runs,
            many=True
        )

        return Response(serializer.data)