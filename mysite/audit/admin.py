from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        'actor',
        'workspace',
        'action',
        'object_type',
        'created_at',
    )

    list_filter = (
        'action',
        'created_at',
    )

    search_fields = (
        'actor__username',
        'workspace__name',
        'description',
        'object_type',
        'object_id',
    )

    readonly_fields = (
        'actor',
        'workspace',
        'action',
        'object_type',
        'object_id',
        'description',
        'metadata',
        'ip_address',
        'user_agent',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False