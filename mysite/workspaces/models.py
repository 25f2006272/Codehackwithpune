from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Workspace(models.Model):

    class WorkspaceType(models.TextChoices):
        COMPANY = 'COMPANY', 'Company'
        HACKATHON = 'HACKATHON', 'Hackathon Team'
        STUDENT = 'STUDENT', 'Student Team'
        STARTUP = 'STARTUP', 'Startup'
        RESEARCH = 'RESEARCH', 'Research Group'
        VOLUNTEER = 'VOLUNTEER', 'Volunteer Group'
        PERSONAL = 'PERSONAL', 'Personal Project Team'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        ARCHIVED = 'ARCHIVED', 'Archived'

    name = models.CharField(
        max_length=150
    )

    slug = models.SlugField(
        max_length=180,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    workspace_type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.OTHER
    )

    logo_url = models.URLField(
        blank=True
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_workspaces'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_workspaces'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'workspaces'
        ordering = ['-created_at']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

        indexes = [
            models.Index(
                fields=['status', 'workspace_type'],
                name='workspace_status_type_idx'
            ),
        ]

    def __str__(self):
        return self.name
    
    
class WorkspaceMembership(models.Model):

    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Workspace Owner'
        ADMIN = 'ADMIN', 'Workspace Admin'
        MEMBER = 'MEMBER', 'Member'
        VIEWER = 'VIEWER', 'Viewer'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        LEFT = 'LEFT', 'Left'
        REMOVED = 'REMOVED', 'Removed'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_workspace_members'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'workspace_memberships'

        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'user'],
                name='unique_workspace_member'
            ),

            models.UniqueConstraint(
                fields=['workspace'],
                condition=models.Q(
                    role='OWNER',
                    status='ACTIVE'
                ),
                name='unique_active_workspace_owner'
            ),
        ]

        indexes = [
            models.Index(
                fields=['workspace', 'status'],
                name='ws_member_status_idx'
            ),
            models.Index(
                fields=['user', 'status'],
                name='user_member_status_idx'
            ),
        ]

        verbose_name = 'Workspace Membership'
        verbose_name_plural = 'Workspace Memberships'

    def __str__(self):
        return f'{self.user.username} - {self.workspace.name} ({self.role})'
    

import uuid


class WorkspaceInvitation(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        EXPIRED = 'EXPIRED', 'Expired'
        REVOKED = 'REVOKED', 'Revoked'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='invitations'
    )

    email = models.EmailField()

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_workspace_invitations'
    )

    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_workspace_invitations'
    )

    invited_role = models.CharField(
        max_length=20,
        choices=[
            ('ADMIN', 'Workspace Admin'),
            ('MEMBER', 'Member'),
            ('VIEWER', 'Viewer'),
        ],
        default='MEMBER'
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    expires_at = models.DateTimeField()

    accepted_at = models.DateTimeField(
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
        db_table = 'workspace_invitations'

        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'email'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_ws_invite'
            )
        ]

        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} - {self.workspace.name}'