from rest_framework import serializers

from .models import Folder


class FolderCreateSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=150)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )

    parent_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None
    )

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Folder name is required."
            )

        return value


class FolderUpdateSerializer(serializers.Serializer):

    name = serializers.CharField(
        max_length=150,
        required=False
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate(self, attrs):

        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )

        return attrs

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Folder name cannot be empty."
            )

        return value


class FolderReadSerializer(serializers.ModelSerializer):

    workspace_id = serializers.IntegerField(read_only=True)

    parent_id = serializers.IntegerField(
        source="parent.id",
        read_only=True,
        allow_null=True
    )

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True
    )

    subfolder_count = serializers.IntegerField(read_only=True)

    file_count = serializers.IntegerField(read_only=True)

    class Meta:

        model = Folder

        fields = [
            "id",
            "workspace_id",
            "parent_id",
            "parent_name",
            "name",
            "description",
            "created_by_username",
            "is_archived",
            "subfolder_count",
            "file_count",
            "created_at",
            "updated_at"
        ]


class FolderMoveSerializer(serializers.Serializer):

    parent_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None
    )