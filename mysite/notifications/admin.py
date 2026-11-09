from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        'recipient',
        'title',
        'notification_type',
        'workspace',
        'read_at',
        'created_at',
    )

    list_filter = (
        'notification_type',
        'read_at',
        'created_at',
    )

    search_fields = (
        'recipient__username',
        'title',
        'message',
    )

    readonly_fields = (
        'created_at',
    )