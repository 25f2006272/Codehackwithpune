from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):

    class Status(models.TextChoices):
        PLANNING = 'PLANNING', 'Planning'
        ACTIVE = 'ACTIVE', 'Active'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        COMPLETED = 'COMPLETED', 'Completed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='projects'
    )

    name = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        max_length=220
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects'
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    target_end_date = models.DateField(
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
        db_table = 'projects'

        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'slug'],
                name='unique_workspace_project_slug'
            )
        ]

        indexes = [
            models.Index(
                fields=['workspace', 'status'],
                name='project_status_idx'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.workspace.name})'


class ProjectMembership(models.Model):

    class Role(models.TextChoices):
        LEAD = 'LEAD', 'Team Lead'
        MEMBER = 'MEMBER', 'Project Member'
        VIEWER = 'VIEWER', 'Project Viewer'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        LEFT = 'LEFT', 'Left'
        REMOVED = 'REMOVED', 'Removed'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )

    project_role = models.CharField(
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
        related_name='added_project_members'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'project_memberships'

        constraints = [
            models.UniqueConstraint(
                fields=['project', 'user'],
                name='unique_project_member'
            ),

            models.UniqueConstraint(
                fields=['project'],
                condition=models.Q(
                    project_role='LEAD',
                    status='ACTIVE'
                ),
                name='unique_active_project_lead'
            ),
        ]

        indexes = [
            models.Index(
                fields=['project', 'status'],
                name='proj_member_status_idx'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.project.name} ({self.project_role})'


class ProjectTask(models.Model):

    class Status(models.TextChoices):
        TODO = 'TODO', 'To Do'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        BLOCKED = 'BLOCKED', 'Blocked'
        DONE = 'DONE', 'Done'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    title = models.CharField(
        max_length=250
    )

    description = models.TextField(
        blank=True
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_project_tasks'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_project_tasks'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    due_date = models.DateField(
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
        db_table = 'project_tasks'

        ordering = ['due_date', '-created_at']

        indexes = [
            models.Index(
                fields=['project', 'status'],
                name='task_project_status_idx'
            ),
            models.Index(
                fields=['assigned_to', 'status'],
                name='task_assignee_status_idx'
            )
        ]

    def __str__(self):
        return self.title


class ProjectDecision(models.Model):

    class DecisionStatus(models.TextChoices):
        PROPOSED = 'PROPOSED', 'Proposed'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'

    class DecisionType(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical'
        PRODUCT = 'PRODUCT', 'Product'
        PROCESS = 'PROCESS', 'Process'
        OTHER = 'OTHER', 'Other'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='decisions'
    )

    title = models.CharField(
        max_length=250
    )

    context = models.TextField(
        blank=True
    )

    decision = models.TextField()

    rationale = models.TextField(
        blank=True
    )

    decision_type = models.CharField(
        max_length=20,
        choices=DecisionType.choices,
        default=DecisionType.OTHER
    )

    status = models.CharField(
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PROPOSED
    )

    decision_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_project_decisions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'project_decisions'

        ordering = ['-decision_date', '-created_at']

        indexes = [
            models.Index(
                fields=['project', 'status'],
                name='decision_project_status_idx'
            )
        ]

    def __str__(self):
        return self.title


class ProjectActivity(models.Model):

    class ActivityType(models.TextChoices):
        PROJECT_CREATED = 'PROJECT_CREATED', 'Project Created'
        MEMBER_ADDED = 'MEMBER_ADDED', 'Member Added'
        MEMBER_REMOVED = 'MEMBER_REMOVED', 'Member Removed'
        TASK_CREATED = 'TASK_CREATED', 'Task Created'
        TASK_UPDATED = 'TASK_UPDATED', 'Task Updated'
        DECISION_RECORDED = 'DECISION_RECORDED', 'Decision Recorded'
        FILE_LINKED = 'FILE_LINKED', 'File Linked'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
        OTHER = 'OTHER', 'Other'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_activities'
    )

    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
        default=ActivityType.OTHER
    )

    description = models.TextField()

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'project_activities'

        ordering = ['-created_at']

        indexes = [
            models.Index(
                fields=['project', '-created_at'],
                name='project_activity_idx'
            )
        ]

    def __str__(self):
        return f'{self.activity_type} - {self.project.name}'