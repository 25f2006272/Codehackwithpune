from rest_framework import serializers

from .models import FileVersion


class FileVersionUploadSerializer(serializers.Serializer):

    file = serializers.FileField()

    def validate_file(self, value):

        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError(
                "Maximum allowed file size is 50 MB."
            )

        return value


class FileVersionReadSerializer(serializers.ModelSerializer):

    uploaded_by_username = serializers.SerializerMethodField()

    is_current = serializers.SerializerMethodField()

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
            "is_current",
            "created_at",
        ]

    def get_uploaded_by_username(self, obj):

        if obj.uploaded_by:
            return obj.uploaded_by.username

        return None

    def get_is_current(self, obj):

        asset = obj.file_asset

        return asset.current_version_id == obj.id