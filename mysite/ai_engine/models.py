from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, F


# =====================================================
# 1. DOCUMENT EXTRACTION
# =====================================================

class DocumentExtraction(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    file_version = models.ForeignKey(
        'filemanager.FileVersion',
        on_delete=models.PROTECT,
        related_name='extractions'
    )

    extraction_version = models.PositiveIntegerField(
        default=1
    )

    extractor_name = models.CharField(
        max_length=100,
        blank=True
    )

    extracted_text = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    error_message = models.TextField(
        blank=True
    )

    extracted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_extractions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'document_extractions'

        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['file_version', 'extraction_version'],
                name='unique_file_extraction_version'
            )
        ]

        indexes = [
            models.Index(
                fields=['file_version', 'status'],
                name='extraction_file_status_idx'
            )
        ]

    def __str__(self):

        return (
            f'{self.file_version.original_filename} '
            f'- Extraction {self.extraction_version}'
        )


# =====================================================
# 2. DOCUMENT CHUNKS
# =====================================================

class DocumentChunk(models.Model):

    extraction = models.ForeignKey(
        DocumentExtraction,
        on_delete=models.CASCADE,
        related_name='chunks'
    )

    chunk_index = models.PositiveIntegerField()

    content = models.TextField()

    page_number = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    section_title = models.CharField(
        max_length=255,
        blank=True
    )

    token_count = models.PositiveIntegerField(
        default=0
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'document_chunks'

        ordering = ['chunk_index']

        constraints = [
            models.UniqueConstraint(
                fields=['extraction', 'chunk_index'],
                name='unique_extraction_chunk'
            )
        ]

        indexes = [
            models.Index(
                fields=['extraction', 'chunk_index'],
                name='chunk_extraction_idx'
            )
        ]

    def __str__(self):

        return (
            f'Chunk {self.chunk_index} - '
            f'{self.extraction_id}'
        )


# =====================================================
# 3. ANALYSIS RUN
# =====================================================

class AnalysisRun(models.Model):

    class Status(models.TextChoices):

        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class RunType(models.TextChoices):

        FULL = 'FULL', 'Full Analysis'
        INCREMENTAL = 'INCREMENTAL', 'Incremental Analysis'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='analysis_runs'
    )

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_analysis_runs'
    )

    provider = models.CharField(
        max_length=50,
        default='GEMINI'
    )

    model_name = models.CharField(
        max_length=100,
        default='Gemini Flash'
    )

    run_type = models.CharField(
        max_length=20,
        choices=RunType.choices,
        default=RunType.FULL
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    prompt_version = models.CharField(
        max_length=50,
        blank=True
    )

    input_tokens = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    output_tokens = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True
    )

    error_message = models.TextField(
        blank=True
    )

    configuration = models.JSONField(
        default=dict,
        blank=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'analysis_runs'

        ordering = ['-created_at']

        indexes = [
            models.Index(
                fields=['project', 'status'],
                name='analysis_project_status_idx'
            )
        ]

    def __str__(self):

        return (
            f'{self.project.name} - '
            f'{self.model_name} - {self.status}'
        )


# =====================================================
# 4. ANALYSIS SOURCE
# =====================================================

class AnalysisSource(models.Model):

    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name='sources'
    )

    extraction = models.ForeignKey(
        DocumentExtraction,
        on_delete=models.PROTECT,
        related_name='analysis_sources'
    )

    source_order = models.PositiveIntegerField(
        default=0
    )

    relevance_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'analysis_sources'

        constraints = [
            models.UniqueConstraint(
                fields=['analysis_run', 'extraction'],
                name='unique_analysis_source'
            )
        ]

    def clean(self):

        if (
            self.analysis_run_id
            and self.extraction_id
            and self.analysis_run.project.workspace_id
            != self.extraction.file_version.file_asset.workspace_id
        ):

            raise ValidationError(
                "Analysis and source must belong to the same workspace."
            )

    def __str__(self):

        return (
            f'{self.analysis_run_id} - '
            f'{self.extraction_id}'
        )


# =====================================================
# 5. KNOWLEDGE ITEM
# =====================================================

class KnowledgeItem(models.Model):

    class ItemType(models.TextChoices):

        DECISION = 'DECISION', 'Decision'
        TASK = 'TASK', 'Task'
        OWNERSHIP = 'OWNERSHIP', 'Ownership'
        RISK = 'RISK', 'Risk'
        BLOCKER = 'BLOCKER', 'Blocker'
        DEPENDENCY = 'DEPENDENCY', 'Dependency'
        OPEN_QUESTION = 'OPEN_QUESTION', 'Open Question'
        NEXT_ACTION = 'NEXT_ACTION', 'Next Action'
        CONTACT = 'CONTACT', 'Important Contact'
        OTHER = 'OTHER', 'Other'

    class VerificationStatus(models.TextChoices):

        NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs Review'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'

    class Priority(models.TextChoices):

        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='knowledge_items'
    )

    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.PROTECT,
        related_name='knowledge_items'
    )

    item_type = models.CharField(
        max_length=30,
        choices=ItemType.choices
    )

    title = models.CharField(
        max_length=255
    )

    description = models.TextField()

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NEEDS_REVIEW
    )

    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_knowledge_items'
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'knowledge_items'

        ordering = ['-created_at']

        indexes = [

            models.Index(
                fields=['project', 'item_type'],
                name='knowledge_project_type_idx'
            ),

            models.Index(
                fields=['project', 'verification_status'],
                name='knowledge_project_status_idx'
            )

        ]

    def clean(self):

        if (
            self.analysis_run_id
            and self.project_id
            and self.analysis_run.project_id != self.project_id
        ):

            raise ValidationError(
                "Analysis run must belong to the same project."
            )

    def __str__(self):

        return f'{self.item_type} - {self.title}'


# =====================================================
# 6. EVIDENCE
# =====================================================

class Evidence(models.Model):

    knowledge_item = models.ForeignKey(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='evidence'
    )

    document_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        related_name='evidence_records'
    )

    quoted_text = models.TextField()

    start_char = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    end_char = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    relevance_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'evidence'

        ordering = ['-created_at']

        constraints = [

            models.UniqueConstraint(
                fields=['knowledge_item', 'document_chunk'],
                name='unique_knowledge_evidence'
            )

        ]

        indexes = [

            models.Index(
                fields=['knowledge_item'],
                name='evidence_knowledge_idx'
            )

        ]

    def clean(self):

        if (
            self.knowledge_item_id
            and self.document_chunk_id
        ):

            extraction = self.document_chunk.extraction

            source_workspace_id = (
                extraction.file_version.file_asset.workspace_id
            )

            knowledge_workspace_id = (
                self.knowledge_item.project.workspace_id
            )

            if source_workspace_id != knowledge_workspace_id:

                raise ValidationError(
                    "Evidence must belong to the same workspace "
                    "as the knowledge item."
                )

    def __str__(self):

        return f'Evidence for {self.knowledge_item.title}'


# =====================================================
# 7. KNOWLEDGE CONFLICT
# =====================================================

class KnowledgeConflict(models.Model):

    class ResolutionStatus(models.TextChoices):

        OPEN = 'OPEN', 'Open'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        RESOLVED = 'RESOLVED', 'Resolved'
        ACCEPTED_BOTH = 'ACCEPTED_BOTH', 'Both Accepted'
        DISMISSED = 'DISMISSED', 'Dismissed'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='knowledge_conflicts'
    )

    knowledge_item_a = models.ForeignKey(
        KnowledgeItem,
        on_delete=models.PROTECT,
        related_name='conflicts_as_first'
    )

    knowledge_item_b = models.ForeignKey(
        KnowledgeItem,
        on_delete=models.PROTECT,
        related_name='conflicts_as_second'
    )

    description = models.TextField()

    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.OPEN
    )

    resolution_notes = models.TextField(
        blank=True
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_knowledge_conflicts'
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'knowledge_conflicts'

        ordering = ['-created_at']

        constraints = [

            models.CheckConstraint(
                condition=~Q(
                    knowledge_item_a=F('knowledge_item_b')
                ),
                name='conflict_items_must_differ'
            )

        ]

        indexes = [

            models.Index(
                fields=['project', 'resolution_status'],
                name='conflict_project_status_idx'
            )

        ]

    def clean(self):

        if self.project_id and self.knowledge_item_a_id:

            if self.knowledge_item_a.project_id != self.project_id:

                raise ValidationError(
                    "First knowledge item must belong to this project."
                )

        if self.project_id and self.knowledge_item_b_id:

            if self.knowledge_item_b.project_id != self.project_id:

                raise ValidationError(
                    "Second knowledge item must belong to this project."
                )

    def __str__(self):

        return f'Conflict - {self.project.name}'