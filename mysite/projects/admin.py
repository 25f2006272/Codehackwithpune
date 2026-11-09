from django.contrib import admin

from .models import (
    Project,
    ProjectMembership,
    ProjectTask,
    ProjectDecision,
    ProjectActivity,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'workspace',
        'status',
        'created_by',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'name',
        'workspace__name',
    )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):

    list_display = (
        'project',
        'user',
        'project_role',
        'status',
        'joined_at',
    )

    list_filter = (
        'project_role',
        'status',
    )

    search_fields = (
        'project__name',
        'user__username',
    )


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'project',
        'assigned_to',
        'status',
        'priority',
        'due_date',
    )

    list_filter = (
        'status',
        'priority',
    )

    search_fields = (
        'title',
        'project__name',
    )


@admin.register(ProjectDecision)
class ProjectDecisionAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'project',
        'decision_type',
        'status',
        'decision_date',
    )

    list_filter = (
        'decision_type',
        'status',
    )

    search_fields = (
        'title',
        'project__name',
    )


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):

    list_display = (
        'project',
        'actor',
        'activity_type',
        'created_at',
    )

    list_filter = (
        'activity_type',
        'created_at',
    )

    search_fields = (
        'project__name',
        'description',
    )

    readonly_fields = (
        'created_at',
    )