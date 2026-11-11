from rest_framework import serializers

from .models import DocumentExtraction, DocumentChunk


class ExtractionRequestSerializer(serializers.Serializer):

    force = serializers.BooleanField(
        required=False,
        default=False
    )


class DocumentExtractionReadSerializer(serializers.ModelSerializer):

    original_filename = serializers.CharField(
        source="file_version.original_filename",
        read_only=True
    )

    file_version_id = serializers.IntegerField(
        read_only=True
    )

    chunk_count = serializers.SerializerMethodField()

    text_length = serializers.SerializerMethodField()

    class Meta:

        model = DocumentExtraction

        fields = [
            "id",
            "file_version_id",
            "original_filename",
            "extraction_version",
            "extractor_name",
            "status",
            "error_message",
            "chunk_count",
            "text_length",
            "extracted_at",
            "created_at",
        ]

    def get_chunk_count(self, obj):

        return obj.chunks.count()

    def get_text_length(self, obj):

        return len(obj.extracted_text)


class DocumentChunkReadSerializer(serializers.ModelSerializer):

    class Meta:

        model = DocumentChunk

        fields = [
            "id",
            "chunk_index",
            "content",
            "page_number",
            "section_title",
            "token_count",
            "metadata",
            "created_at",
        ]