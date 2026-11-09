from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q, F


# =====================================================
# 1. HANDOVER MODEL
# =====================================================

class Handover(models.Model):

    class Status(models.TextChoices):

        DRAFT = 'DRAFT', 'Draft'
        PROCESSING = 'PROCESSING', 'Processing'
        IN_REVIEW = 'IN_REVIEW', 'In Review'
        CHANGES_REQUESTED = 'CHANGES_REQUESTED', 'Changes Requested'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SHARED = 'SHARED', 'Shared'
        ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
        CANCELLED = 'CANCELLED', 'Cancelled'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        related_name='handovers'
    )

    title = models.CharField(
        max_length=255
    )

    departing_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='outgoing_handovers'
    )

    incoming_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='incoming_handovers'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_handovers'
    )

    summary = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    shared_at = models.DateTimeField(
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

        db_table = 'handovers'

        ordering = ['-created_at']

        constraints = [

            models.CheckConstraint(
                condition=~Q(
                    departing_member=F('incoming_member')
                ),
                name='handover_members_must_differ'
            )

        ]

        indexes = [

            models.Index(
                fields=['project', 'status'],
                name='handover_project_status_idx'
            ),

            models.Index(
                fields=['incoming_member', 'status'],
                name='handover_incoming_status_idx'
            ),

        ]

    def clean(self):

        if self.departing_member_id == self.incoming_member_id:

            raise ValidationError(
                "Departing and incoming members must be different."
            )

    def __str__(self):

        return f'{self.title} - {self.project.name}'


# =====================================================
# 2. HANDOVER ITEM MODEL
# =====================================================

class HandoverItem(models.Model):

    class Category(models.TextChoices):

        OVERVIEW = 'OVERVIEW', 'Project Overview'
        DECISION = 'DECISION', 'Important Decision'
        TASK = 'TASK', 'Pending Task'
        OWNERSHIP = 'OWNERSHIP', 'Ownership'
        RISK = 'RISK', 'Risk'
        BLOCKER = 'BLOCKER', 'Blocker'
        DEPENDENCY = 'DEPENDENCY', 'Dependency'
        OPEN_QUESTION = 'OPEN_QUESTION', 'Open Question'
        NEXT_ACTION = 'NEXT_ACTION', 'Next Action'
        CONTACT = 'CONTACT', 'Important Contact'
        DOCUMENTATION = 'DOCUMENTATION', 'Documentation'
        OTHER = 'OTHER', 'Other'

    class Priority(models.TextChoices):

        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        related_name='items'
    )

    knowledge_item = models.ForeignKey(
        'ai_engine.KnowledgeItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_items'
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER
    )

    title = models.CharField(
        max_length=255
    )

    content = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    # Preserve source details used when the item was added.
    source_snapshot = models.JSONField(
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

        db_table = 'handover_items'

        ordering = ['sort_order', 'created_at']

        indexes = [

            models.Index(
                fields=['handover', 'category'],
                name='handover_item_category_idx'
            )

        ]

    def clean(self):

        if self.knowledge_item_id and self.handover_id:

            if (
                self.knowledge_item.project_id
                != self.handover.project_id
            ):

                raise ValidationError(
                    "Knowledge item must belong to the same project."
                )

    def __str__(self):

        return f'{self.title} - {self.handover.title}'


# =====================================================
# 3. HANDOVER VERSION MODEL
# =====================================================

class HandoverVersion(models.Model):

    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.PositiveIntegerField()

    # Complete snapshot of the handover at this version.
    snapshot = models.JSONField(
        default=dict
    )

    change_summary = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_handover_versions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'handover_versions'

        ordering = ['-version_number']

        constraints = [

            models.UniqueConstraint(
                fields=['handover', 'version_number'],
                name='unique_handover_version'
            )

        ]

    def __str__(self):

        return (
            f'{self.handover.title} '
            f'- Version {self.version_number}'
        )


# =====================================================
# 4. HANDOVER REVIEW MODEL
# =====================================================

class HandoverReview(models.Model):

    class Decision(models.TextChoices):

        APPROVED = 'APPROVED', 'Approved'
        CHANGES_REQUESTED = 'CHANGES_REQUESTED', 'Changes Requested'
        REJECTED = 'REJECTED', 'Rejected'

    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='handover_reviews'
    )

    reviewed_version = models.ForeignKey(
        HandoverVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews'
    )

    decision = models.CharField(
        max_length=30,
        choices=Decision.choices
    )

    comments = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'handover_reviews'

        ordering = ['-created_at']

        indexes = [

            models.Index(
                fields=['handover', 'decision'],
                name='review_handover_decision_idx'
            )

        ]

    def clean(self):

        if (
            self.reviewed_version_id
            and self.handover_id
            and self.reviewed_version.handover_id != self.handover_id
        ):

            raise ValidationError(
                "Reviewed version must belong to this handover."
            )

    def __str__(self):

        return (
            f'{self.handover.title} '
            f'- {self.reviewer.username} '
            f'- {self.decision}'
        )


# =====================================================
# 5. HANDOVER ACKNOWLEDGEMENT MODEL
# =====================================================

class HandoverAcknowledgement(models.Model):

    class Status(models.TextChoices):

        PENDING = 'PENDING', 'Pending'
        ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
        NEEDS_CLARIFICATION = 'NEEDS_CLARIFICATION', 'Needs Clarification'

    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        related_name='acknowledgements'
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='handover_acknowledgements'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    comments = models.TextField(
        blank=True
    )

    acknowledged_at = models.DateTimeField(
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

        db_table = 'handover_acknowledgements'

        constraints = [

            models.UniqueConstraint(
                fields=['handover', 'recipient'],
                name='unique_handover_recipient'
            )

        ]

        indexes = [

            models.Index(
                fields=['recipient', 'status'],
                name='ack_recipient_status_idx'
            )

        ]

    def clean(self):

        if (
            self.handover_id
            and self.recipient_id
            and self.handover.incoming_member_id != self.recipient_id
        ):

            raise ValidationError(
                "Only the assigned incoming member can acknowledge "
                "this handover."
            )

    def __str__(self):

        return (
            f'{self.handover.title} '
            f'- {self.recipient.username} '
            f'- {self.status}'
        )