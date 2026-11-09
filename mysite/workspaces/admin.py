from django.contrib import admin
from .models import (
    Workspace,
    WorkspaceMembership,
    WorkspaceInvitation,
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'workspace_type',
        'owner',
        'status',
        'created_at',
    )

    search_fields = (
        'name',
        'owner__username',
    )

    list_filter = (
        'workspace_type',
        'status',
    )


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):

    list_display = (
        'workspace',
        'user',
        'role',
        'status',
        'joined_at',
    )

    list_filter = (
        'role',
        'status',
    )

    search_fields = (
        'workspace__name',
        'user__username',
    )


@admin.register(WorkspaceInvitation)
class WorkspaceInvitationAdmin(admin.ModelAdmin):

    list_display = (
        'workspace',
        'email',
        'invited_role',
        'status',
        'expires_at',
    )

    list_filter = (
        'status',
        'invited_role',
    )

    search_fields = (
        'workspace__name',
        'email',
    )

    readonly_fields = (
        'token',
        'created_at',
        'updated_at',
    )