from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    class Action(models.TextChoices):

        USER_LOGIN = 'USER_LOGIN', 'User Login'
        USER_LOGOUT = 'USER_LOGOUT', 'User Logout'

        WORKSPACE_CREATED = 'WORKSPACE_CREATED', 'Workspace Created'
        WORKSPACE_UPDATED = 'WORKSPACE_UPDATED', 'Workspace Updated'
        WORKSPACE_DELETED = 'WORKSPACE_DELETED', 'Workspace Deleted'

        MEMBER_INVITED = 'MEMBER_INVITED', 'Member Invited'
        MEMBER_JOINED = 'MEMBER_JOINED', 'Member Joined'
        MEMBER_REMOVED = 'MEMBER_REMOVED', 'Member Removed'

        ROLE_PROMOTED = 'ROLE_PROMOTED', 'Role Promoted'
        ROLE_DEMOTED = 'ROLE_DEMOTED', 'Role Demoted'
        OWNERSHIP_TRANSFERRED = 'OWNERSHIP_TRANSFERRED', 'Ownership Transferred'

        PROJECT_CREATED = 'PROJECT_CREATED', 'Project Created'
        PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project Updated'
        PROJECT_DELETED = 'PROJECT_DELETED', 'Project Deleted'

        FILE_UPLOADED = 'FILE_UPLOADED', 'File Uploaded'
        FILE_DOWNLOADED = 'FILE_DOWNLOADED', 'File Downloaded'
        FILE_DELETED = 'FILE_DELETED', 'File Deleted'
        FILE_MOVED = 'FILE_MOVED', 'File Moved'

        HANDOVER_CREATED = 'HANDOVER_CREATED', 'Handover Created'
        HANDOVER_APPROVED = 'HANDOVER_APPROVED', 'Handover Approved'
        HANDOVER_REJECTED = 'HANDOVER_REJECTED', 'Handover Rejected'
        HANDOVER_SHARED = 'HANDOVER_SHARED', 'Handover Shared'

        PERMISSION_CHANGED = 'PERMISSION_CHANGED', 'Permission Changed'

        OTHER = 'OTHER', 'Other'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices
    )

    object_type = models.CharField(
        max_length=100,
        blank=True
    )

    object_id = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = 'audit_logs'

        ordering = ['-created_at']

        indexes = [

            models.Index(
                fields=['workspace', '-created_at'],
                name='audit_workspace_date_idx'
            ),

            models.Index(
                fields=['actor', '-created_at'],
                name='audit_actor_date_idx'
            ),

            models.Index(
                fields=['action', '-created_at'],
                name='audit_action_date_idx'
            ),

            models.Index(
                fields=['object_type', 'object_id'],
                name='audit_object_idx'
            )

        ]

    def __str__(self):

        return f'{self.action} - {self.created_at}'