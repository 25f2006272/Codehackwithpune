from django.contrib import admin

from .models import (
    Handover,
    HandoverItem,
    HandoverReview,
    HandoverVersion,
    HandoverAcknowledgement,
)


@admin.register(Handover)
class HandoverAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'project',
        'departing_member',
        'incoming_member',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'title',
        'project__name',
        'departing_member__username',
        'incoming_member__username',
    )


@admin.register(HandoverItem)
class HandoverItemAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'handover',
        'category',
        'priority',
        'sort_order',
    )

    list_filter = (
        'category',
        'priority',
    )

    search_fields = (
        'title',
        'content',
    )


@admin.register(HandoverReview)
class HandoverReviewAdmin(admin.ModelAdmin):

    list_display = (
        'handover',
        'reviewer',
        'reviewed_version',
        'decision',
        'created_at',
    )

    list_filter = (
        'decision',
        'created_at',
    )

    search_fields = (
        'handover__title',
        'reviewer__username',
        'comments',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(HandoverVersion)
class HandoverVersionAdmin(admin.ModelAdmin):

    list_display = (
        'handover',
        'version_number',
        'created_by',
        'created_at',
    )

    search_fields = (
        'handover__title',
        'change_summary',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(HandoverAcknowledgement)
class HandoverAcknowledgementAdmin(admin.ModelAdmin):

    list_display = (
        'handover',
        'recipient',
        'status',
        'acknowledged_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'handover__title',
        'recipient__username',
    )