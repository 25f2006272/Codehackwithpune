from rest_framework import serializers

from .models import (
    AnalysisRun,
    KnowledgeItem,
)


class AnalysisRequestSerializer(serializers.Serializer):

    file_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=20,
        allow_empty=False,
    )


class AnalysisRunReadSerializer(serializers.ModelSerializer):

    project_name = serializers.CharField(
        source="project.name",
        read_only=True
    )

    project_summary = serializers.SerializerMethodField()

    knowledge_item_count = serializers.SerializerMethodField()

    conflict_count = serializers.SerializerMethodField()

    class Meta:

        model = AnalysisRun

        fields = [
            "id",
            "project",
            "project_name",
            "provider",
            "model_name",
            "run_type",
            "status",
            "input_tokens",
            "output_tokens",
            "error_message",
            "project_summary",
            "knowledge_item_count",
            "conflict_count",
            "started_at",
            "completed_at",
            "created_at",
        ]

    def get_project_summary(self, obj):

        return obj.configuration.get(
            "project_summary",
            ""
        )

    def get_knowledge_item_count(self, obj):

        return obj.knowledge_items.count()

    def get_conflict_count(self, obj):

        return obj.project.knowledge_conflicts.filter(
            knowledge_item_a__analysis_run=obj
        ).count()


class KnowledgeItemReadSerializer(serializers.ModelSerializer):

    assigned_to_username = serializers.SerializerMethodField()

    evidence = serializers.SerializerMethodField()

    class Meta:

        model = KnowledgeItem

        fields = [
            "id",
            "analysis_run_id",
            "item_type",
            "title",
            "description",
            "verification_status",
            "confidence_score",
            "priority",
            "assigned_to_username",
            "due_date",
            "metadata",
            "evidence",
            "created_at",
        ]

    def get_assigned_to_username(self, obj):

        if obj.assigned_to:
            return obj.assigned_to.username

        return None

    def get_evidence(self, obj):

        result = []

        for evidence in obj.evidence.all():

            chunk = evidence.document_chunk

            extraction = chunk.extraction

            result.append({
                "chunk_id": chunk.id,
                "file_version_id": extraction.file_version_id,
                "filename": extraction.file_version.original_filename,
                "page_number": chunk.page_number,
                "quoted_text": evidence.quoted_text,
                "start_char": evidence.start_char,
                "end_char": evidence.end_char,
                "relevance_score": evidence.relevance_score,
            })

        return result