from django.db import models
from django.conf import settings


class Notification(models.Model):

    class NotificationType(models.TextChoices):

        WORKSPACE_INVITATION = 'WORKSPACE_INVITATION', 'Workspace Invitation'
        INVITATION_ACCEPTED = 'INVITATION_ACCEPTED', 'Invitation Accepted'

        MEMBER_ADDED = 'MEMBER_ADDED', 'Member Added'
        ROLE_CHANGED = 'ROLE_CHANGED', 'Role Changed'
        OWNERSHIP_TRANSFERRED = 'OWNERSHIP_TRANSFERRED', 'Ownership Transferred'

        PROJECT_CREATED = 'PROJECT_CREATED', 'Project Created'
        TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task Assigned'
        TASK_UPDATED = 'TASK_UPDATED', 'Task Updated'

        FILE_SHARED = 'FILE_SHARED', 'File Shared'
        FILE_UPLOADED = 'FILE_UPLOADED', 'File Uploaded'

        HANDOVER_SUBMITTED = 'HANDOVER_SUBMITTED', 'Handover Submitted'
        HANDOVER_APPROVED = 'HANDOVER_APPROVED', 'Handover Approved'
        HANDOVER_REJECTED = 'HANDOVER_REJECTED', 'Handover Rejected'
        HANDOVER_SHARED = 'HANDOVER_SHARED', 'Handover Shared'

        GENERAL = 'GENERAL', 'General'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    target_url = models.CharField(
        max_length=500,
        blank=True
    )

    related_object_type = models.CharField(
        max_length=100,
        blank=True
    )

    related_object_id = models.CharField(
        max_length=100,
        blank=True
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'notifications'

        ordering = ['-created_at']

        indexes = [

            models.Index(
                fields=['recipient', '-created_at'],
                name='notification_user_date_idx'
            ),

            models.Index(
                fields=['recipient', 'read_at'],
                name='notification_read_idx'
            ),

            models.Index(
                fields=['workspace', '-created_at'],
                name='notification_ws_date_idx'
            )

        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):

        return f'{self.title} - {self.recipient.username}'