from rest_framework import serializers
from .models import (
    Handover,
    HandoverItem,
    HandoverVersion,
    HandoverReview,
    HandoverAcknowledgement,
)


class HandoverItemSerializer(serializers.ModelSerializer):
    handover_id = serializers.IntegerField(source="handover.pk", read_only=True)
    knowledge_item_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = HandoverItem
        fields = (
            "id", "handover_id", "knowledge_item_id", "category", "title",
            "content", "priority", "sort_order", "source_snapshot",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "handover_id", "knowledge_item_id", "source_snapshot",
            "created_at", "updated_at",
        )


class HandoverReviewSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)
    reviewed_version_number = serializers.IntegerField(source="reviewed_version.version_number", read_only=True, allow_null=True)

    class Meta:
        model = HandoverReview
        fields = (
            "id", "reviewer", "reviewer_username", "reviewed_version",
            "reviewed_version_number", "decision", "comments", "created_at",
        )
        read_only_fields = fields


class HandoverVersionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = HandoverVersion
        fields = (
            "id", "version_number", "snapshot", "change_summary",
            "created_by", "created_by_username", "created_at",
        )
        read_only_fields = fields


class HandoverAcknowledgementSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(source="recipient.username", read_only=True)

    class Meta:
        model = HandoverAcknowledgement
        fields = (
            "id", "handover", "recipient", "recipient_username", "status",
            "comments", "acknowledged_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class HandoverSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    departing_member_id = serializers.IntegerField(read_only=True)
    departing_member_username = serializers.CharField(source="departing_member.username", read_only=True)
    incoming_member_id = serializers.IntegerField(read_only=True)
    incoming_member_username = serializers.CharField(source="incoming_member.username", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    items = HandoverItemSerializer(many=True, read_only=True)
    reviews = HandoverReviewSerializer(many=True, read_only=True)
    acknowledgements = HandoverAcknowledgementSerializer(many=True, read_only=True)

    class Meta:
        model = Handover
        fields = (
            "id", "project_id", "title", "departing_member_id",
            "departing_member_username", "incoming_member_id",
            "incoming_member_username", "created_by", "created_by_username",
            "summary", "status", "submitted_at", "approved_at", "shared_at",
            "items", "reviews", "acknowledgements", "created_at", "updated_at",
        )
        read_only_fields = fields


class HandoverCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    departing_member_id = serializers.IntegerField(min_value=1)
    incoming_member_id = serializers.IntegerField(min_value=1)
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    knowledge_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )
    items = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate(self, attrs):
        if attrs["departing_member_id"] == attrs["incoming_member_id"]:
            raise serializers.ValidationError("Departing and incoming members must be different.")
        if len(attrs["knowledge_item_ids"]) != len(set(attrs["knowledge_item_ids"])):
            raise serializers.ValidationError("Duplicate knowledge_item_ids are not allowed.")
        return attrs


class HandoverItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandoverItem
        fields = ("category", "title", "content", "priority", "sort_order")


class HandoverItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandoverItem
        fields = ("category", "title", "content", "priority", "sort_order")


class HandoverReviewCreateSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=HandoverReview.Decision.choices)
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class HandoverAcknowledgementCreateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        HandoverAcknowledgement.Status.ACKNOWLEDGED,
        HandoverAcknowledgement.Status.NEEDS_CLARIFICATION,
    ))
    comments = serializers.CharField(required=False, allow_blank=True, default="")
