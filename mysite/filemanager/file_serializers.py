from rest_framework import serializers

from .models import FileAsset, FileVersion


class FileUploadSerializer(serializers.Serializer):

    file = serializers.FileField()

    folder_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_file(self, value):
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError(
                "Maximum allowed file size is 50 MB."
            )

        return value


class FileVersionSummarySerializer(serializers.ModelSerializer):

    uploaded_by_username = serializers.SerializerMethodField()

    class Meta:
        model = FileVersion

        fields = [
            "id",
            "version_number",
            "original_filename",
            "mime_type",
            "file_size",
            "checksum",
            "uploaded_by_username",
            "created_at",
        ]

    def get_uploaded_by_username(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.username

        return None


class FileAssetReadSerializer(serializers.ModelSerializer):

    workspace_id = serializers.IntegerField(read_only=True)
    folder_id = serializers.IntegerField(read_only=True)

    folder_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    current_version = FileVersionSummarySerializer(read_only=True)

    class Meta:
        model = FileAsset

        fields = [
            "id",
            "workspace_id",
            "folder_id",
            "folder_name",
            "name",
            "description",
            "status",
            "created_by_username",
            "current_version",
            "created_at",
            "updated_at",
        ]

    def get_folder_name(self, obj):
        if obj.folder:
            return obj.folder.name

        return None

    def get_created_by_username(self, obj):
        if obj.created_by:
            return obj.created_by.username

        return None