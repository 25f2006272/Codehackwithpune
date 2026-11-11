from rest_framework import serializers
from django.contrib.auth import get_user_model

from workspaces.models import WorkspaceMembership
from projects.models import ProjectMembership

from .models import Evidence, KnowledgeItem, KnowledgeConflict

User = get_user_model()


class EvidenceSerializer(serializers.ModelSerializer):
    document_chunk_id = serializers.IntegerField(read_only=True)
    source_filename = serializers.CharField(
        source="document_chunk.extraction.file_version.file_asset.name",
        read_only=True,
    )
    source_file_id = serializers.IntegerField(
        source="document_chunk.extraction.file_version.file_asset_id",
        read_only=True,
    )
    source_version_id = serializers.IntegerField(
        source="document_chunk.extraction.file_version_id",
        read_only=True,
    )
    page_number = serializers.IntegerField(
        source="document_chunk.page_number",
        read_only=True,
        allow_null=True,
    )
    section_title = serializers.CharField(
        source="document_chunk.section_title",
        read_only=True,
        allow_blank=True,
    )

    class Meta:
        model = Evidence
        fields = (
            "id",
            "document_chunk_id",
            "source_filename",
            "source_file_id",
            "source_version_id",
            "page_number",
            "section_title",
            "quoted_text",
            "start_char",
            "end_char",
            "relevance_score",
            "created_at",
        )
        read_only_fields = fields


class KnowledgeItemSerializer(serializers.ModelSerializer):
    analysis_run_id = serializers.IntegerField(read_only=True)
    project_id = serializers.IntegerField(read_only=True)
    assigned_to_id = serializers.IntegerField(read_only=True, allow_null=True)
    assigned_to_username = serializers.SerializerMethodField()
    evidence = EvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = KnowledgeItem
        fields = (
            "id",
            "project_id",
            "analysis_run_id",
            "item_type",
            "title",
            "description",
            "verification_status",
            "confidence_score",
            "priority",
            "assigned_to_id",
            "assigned_to_username",
            "due_date",
            "metadata",
            "evidence",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_assigned_to_username(self, obj):
        return obj.assigned_to.username if obj.assigned_to_id else None


class KnowledgeItemUpdateSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = KnowledgeItem
        fields = (
            "item_type",
            "title",
            "description",
            "priority",
            "assigned_to",
            "due_date",
        )
        extra_kwargs = {
            "title": {"required": False, "allow_blank": False},
            "description": {"required": False},
            "item_type": {"required": False},
            "priority": {"required": False},
            "due_date": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        item = self.instance
        assigned_user = attrs.get("assigned_to", serializers.empty)
        if assigned_user is not serializers.empty and assigned_user is not None:
            project_member = ProjectMembership.objects.filter(
                project=item.project,
                user=assigned_user,
                status=ProjectMembership.Status.ACTIVE,
            ).exists()
            workspace_member = WorkspaceMembership.objects.filter(
                workspace=item.project.workspace,
                user=assigned_user,
                status=WorkspaceMembership.Status.ACTIVE,
            ).exists()
            if not (project_member or workspace_member):
                raise serializers.ValidationError({
                    "assigned_to": "Assignee must be an active member of this project or workspace."
                })
        return attrs


class ReviewActionSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )


class RejectKnowledgeSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=2000,
    )


class ConflictKnowledgeMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = (
            "id",
            "item_type",
            "title",
            "description",
            "verification_status",
            "confidence_score",
            "priority",
        )
        read_only_fields = fields


class KnowledgeConflictSerializer(serializers.ModelSerializer):
    knowledge_item_a = ConflictKnowledgeMiniSerializer(read_only=True)
    knowledge_item_b = ConflictKnowledgeMiniSerializer(read_only=True)
    resolved_by_username = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeConflict
        fields = (
            "id",
            "project_id",
            "knowledge_item_a",
            "knowledge_item_b",
            "description",
            "resolution_status",
            "resolution_notes",
            "resolved_by_username",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_resolved_by_username(self, obj):
        return obj.resolved_by.username if obj.resolved_by_id else None


class ResolveConflictSerializer(serializers.Serializer):
    resolution_status = serializers.ChoiceField(
        choices=(
            KnowledgeConflict.ResolutionStatus.UNDER_REVIEW,
            KnowledgeConflict.ResolutionStatus.RESOLVED,
            KnowledgeConflict.ResolutionStatus.ACCEPTED_BOTH,
            KnowledgeConflict.ResolutionStatus.DISMISSED,
        )
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
    )
    keep_knowledge_item_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        status = attrs["resolution_status"]
        notes = attrs.get("resolution_notes", "").strip()
        keep_id = attrs.get("keep_knowledge_item_id")

        if status == KnowledgeConflict.ResolutionStatus.RESOLVED:
            if keep_id is None:
                raise serializers.ValidationError({
                    "keep_knowledge_item_id": "Select which conflicting knowledge item should be retained."
                })
            if not notes:
                raise serializers.ValidationError({
                    "resolution_notes": "Explain why this item was retained."
                })
        elif keep_id is not None:
            raise serializers.ValidationError({
                "keep_knowledge_item_id": "This field is only used when resolution_status is RESOLVED."
            })

        if status == KnowledgeConflict.ResolutionStatus.DISMISSED and not notes:
            raise serializers.ValidationError({
                "resolution_notes": "Explain why this conflict is being dismissed."
            })

        return attrs
