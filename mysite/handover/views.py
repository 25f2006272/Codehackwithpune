from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from ai_engine.models import KnowledgeItem
from .models import Handover, HandoverItem, HandoverVersion, HandoverAcknowledgement
from .serializers import (
    HandoverSerializer, HandoverCreateSerializer, HandoverItemSerializer,
    HandoverItemCreateSerializer, HandoverItemUpdateSerializer,
    HandoverVersionSerializer, HandoverReviewSerializer,
    HandoverReviewCreateSerializer, HandoverAcknowledgementSerializer,
    HandoverAcknowledgementCreateSerializer,
)
from .services import (
    get_project_or_404, require_project_read, require_project_manager,
    require_handover_read, require_handover_edit, create_handover,
    create_version, submit_handover, review_handover, share_handover,
    acknowledge_handover, log_handover,
)


class ProjectHandoverListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_project_or_404(project_id)
        require_project_read(request.user, project)
        qs = Handover.objects.filter(project=project).select_related(
            "departing_member", "incoming_member", "created_by"
        ).prefetch_related("items", "reviews", "acknowledgements")
        return Response(HandoverSerializer(qs, many=True).data)

    def post(self, request, project_id):
        project = get_project_or_404(project_id)
        serializer = HandoverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handover = create_handover(request.user, project, serializer.validated_data, request)
        handover = Handover.objects.select_related(
            "project", "departing_member", "incoming_member", "created_by"
        ).prefetch_related("items", "reviews", "acknowledgements").get(pk=handover.pk)
        return Response(HandoverSerializer(handover).data, status=status.HTTP_201_CREATED)


class HandoverDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, handover_id):
        return get_object_or_404(
            Handover.objects.select_related("project__workspace", "departing_member", "incoming_member", "created_by").prefetch_related("items", "reviews", "acknowledgements"),
            pk=handover_id,
        )

    def get(self, request, handover_id):
        handover = self.get_object(handover_id)
        require_handover_read(request.user, handover)
        return Response(HandoverSerializer(handover).data)

    def patch(self, request, handover_id):
        handover = self.get_object(handover_id)
        require_handover_edit(request.user, handover)
        allowed = {"title", "summary"}
        if set(request.data.keys()) - allowed:
            raise ValidationError("Only title and summary can be edited here.")
        if "title" in request.data:
            title = str(request.data["title"]).strip()
            if not title or len(title) > 255:
                raise ValidationError({"title": "Title is required and must be at most 255 characters."})
            handover.title = title
        if "summary" in request.data:
            handover.summary = str(request.data["summary"])
        handover.save(update_fields=["title", "summary", "updated_at"])
        log_handover(request.user, handover, "HANDOVER_UPDATED", f"Updated handover: {handover.title}", request)
        handover.refresh_from_db()
        return Response(HandoverSerializer(handover).data)


class HandoverItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        require_handover_read(request.user, handover)
        return Response(HandoverItemSerializer(handover.items.all(), many=True).data)

    def post(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        require_handover_edit(request.user, handover)
        serializer = HandoverItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = HandoverItem.objects.create(handover=handover, **serializer.validated_data)
        log_handover(request.user, handover, "HANDOVER_ITEM_ADDED", f"Added handover item: {item.title}", request)
        return Response(HandoverItemSerializer(item).data, status=status.HTTP_201_CREATED)


class HandoverItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, item_id):
        return get_object_or_404(HandoverItem.objects.select_related("handover__project__workspace"), pk=item_id)

    def patch(self, request, item_id):
        item = self.get_object(item_id)
        require_handover_edit(request.user, item.handover)
        if item.knowledge_item_id:
            raise ValidationError("AI-derived handover items are snapshots; edit the verified knowledge item and create a new handover version instead.")
        serializer = HandoverItemUpdateSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_handover(request.user, item.handover, "HANDOVER_ITEM_UPDATED", f"Updated handover item: {item.title}", request)
        return Response(HandoverItemSerializer(item).data)

    def delete(self, request, item_id):
        item = self.get_object(item_id)
        require_handover_edit(request.user, item.handover)
        if item.knowledge_item_id:
            raise ValidationError("AI-derived items cannot be removed through this endpoint. Create a new handover draft if the verified knowledge set changes.")
        handover = item.handover
        title = item.title
        item.delete()
        log_handover(request.user, handover, "HANDOVER_ITEM_REMOVED", f"Removed handover item: {title}", request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HandoverSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        handover = submit_handover(request.user, handover, request)
        return Response(HandoverSerializer(handover).data)


class HandoverVersionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        require_handover_read(request.user, handover)
        versions = handover.versions.select_related("created_by").all()
        return Response(HandoverVersionSerializer(versions, many=True).data)


class HandoverReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        require_handover_read(request.user, handover)
        return Response(HandoverReviewSerializer(handover.reviews.select_related("reviewer", "reviewed_version"), many=True).data)

    def post(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        serializer = HandoverReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = review_handover(
            request.user, handover,
            serializer.validated_data["decision"],
            serializer.validated_data["comments"], request,
        )
        return Response(HandoverReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class HandoverShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace", "incoming_member"), pk=handover_id)
        handover = share_handover(request.user, handover, request)
        return Response(HandoverSerializer(handover).data)


class HandoverAcknowledgementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace"), pk=handover_id)
        require_handover_read(request.user, handover)
        ack = handover.acknowledgements.select_related("recipient").all()
        return Response(HandoverAcknowledgementSerializer(ack, many=True).data)

    def post(self, request, handover_id):
        handover = get_object_or_404(Handover.objects.select_related("project__workspace", "incoming_member"), pk=handover_id)
        serializer = HandoverAcknowledgementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ack = acknowledge_handover(
            request.user, handover,
            serializer.validated_data["status"],
            serializer.validated_data["comments"], request,
        )
        return Response(HandoverAcknowledgementSerializer(ack).data)
