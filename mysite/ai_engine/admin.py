from django.contrib import admin

from .models import (
    DocumentExtraction,
    DocumentChunk,
    AnalysisRun,
    AnalysisSource,
    KnowledgeItem,
    Evidence,
    KnowledgeConflict,
)


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(admin.ModelAdmin):

    list_display = (
        'file_version',
        'extraction_version',
        'status',
        'extractor_name',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'file_version__original_filename',
        'extractor_name',
    )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):

    list_display = (
        'extraction',
        'chunk_index',
        'page_number',
        'token_count',
    )

    search_fields = (
        'content',
        'section_title',
    )


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):

    list_display = (
        'project',
        'model_name',
        'run_type',
        'status',
        'initiated_by',
        'created_at',
    )

    list_filter = (
        'status',
        'run_type',
        'provider',
    )

    search_fields = (
        'project__name',
        'model_name',
    )


@admin.register(AnalysisSource)
class AnalysisSourceAdmin(admin.ModelAdmin):

    list_display = (
        'analysis_run',
        'extraction',
        'source_order',
        'relevance_score',
    )


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'project',
        'item_type',
        'verification_status',
        'priority',
        'confidence_score',
    )

    list_filter = (
        'item_type',
        'verification_status',
        'priority',
    )

    search_fields = (
        'title',
        'description',
        'project__name',
    )


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):

    list_display = (
        'knowledge_item',
        'document_chunk',
        'relevance_score',
        'created_at',
    )

    search_fields = (
        'knowledge_item__title',
        'quoted_text',
    )


@admin.register(KnowledgeConflict)
class KnowledgeConflictAdmin(admin.ModelAdmin):

    list_display = (
        'project',
        'knowledge_item_a',
        'knowledge_item_b',
        'resolution_status',
        'resolved_by',
    )

    list_filter = (
        'resolution_status',
    )

    search_fields = (
        'project__name',
        'description',
    )
