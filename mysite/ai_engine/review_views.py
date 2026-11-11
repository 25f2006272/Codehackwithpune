from django.db.models import Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KnowledgeItem, KnowledgeConflict, Evidence
from .review_serializers import (
    KnowledgeItemSerializer,
    KnowledgeItemUpdateSerializer,
    ReviewActionSerializer,
    RejectKnowledgeSerializer,
    KnowledgeConflictSerializer,
    ResolveConflictSerializer,
)
from .review_services import (
    get_project_access,
    get_knowledge_item_for_actor,
    get_conflict_for_actor,
    update_knowledge_item,
    review_knowledge_item,
    resolve_knowledge_conflict,
)


class KnowledgeItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        item = get_knowledge_item_for_actor(request.user, item_id)
        item = KnowledgeItem.objects.select_related(
            "project",
            "analysis_run",
            "assigned_to",
        ).prefetch_related(
            Prefetch(
                "evidence",
                queryset=Evidence.objects.select_related(
                    "document_chunk__extraction__file_version__file_asset"
                ),
            )
        ).get(pk=item.id)
        return Response(KnowledgeItemSerializer(item).data)

    def patch(self, request, item_id):
        item = get_knowledge_item_for_actor(
            request.user,
            item_id,
            reviewer=True,
        )
        serializer = KnowledgeItemUpdateSerializer(
            item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = update_knowledge_item(
            request.user,
            item_id,
            serializer.validated_data,
            request=request,
        )
        return Response(KnowledgeItemSerializer(updated).data)


class VerifyKnowledgeItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = review_knowledge_item(
            actor=request.user,
            item_id=item_id,
            approved=True,
            note=serializer.validated_data.get("note", ""),
            request=request,
        )
        return Response(KnowledgeItemSerializer(item).data, status=status.HTTP_200_OK)


class RejectKnowledgeItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        serializer = RejectKnowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = review_knowledge_item(
            actor=request.user,
            item_id=item_id,
            approved=False,
            note=serializer.validated_data["note"],
            request=request,
        )
        return Response(KnowledgeItemSerializer(item).data, status=status.HTTP_200_OK)


class ProjectConflictListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_project_access(request.user, project_id)
        queryset = KnowledgeConflict.objects.filter(
            project=project
        ).select_related(
            "knowledge_item_a",
            "knowledge_item_b",
            "resolved_by",
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            allowed = {choice for choice, _label in KnowledgeConflict.ResolutionStatus.choices}
            if status_filter not in allowed:
                return Response(
                    {"status": ["Invalid conflict status filter."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(resolution_status=status_filter)

        return Response(KnowledgeConflictSerializer(queryset, many=True).data)


class KnowledgeConflictDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conflict_id):
        conflict = get_conflict_for_actor(request.user, conflict_id)
        return Response(KnowledgeConflictSerializer(conflict).data)


class ResolveKnowledgeConflictView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conflict_id):
        serializer = ResolveConflictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conflict = resolve_knowledge_conflict(
            actor=request.user,
            conflict_id=conflict_id,
            data=serializer.validated_data,
            request=request,
        )
        conflict = KnowledgeConflict.objects.select_related(
            "knowledge_item_a",
            "knowledge_item_b",
            "resolved_by",
        ).get(pk=conflict.id)
        return Response(KnowledgeConflictSerializer(conflict).data)
