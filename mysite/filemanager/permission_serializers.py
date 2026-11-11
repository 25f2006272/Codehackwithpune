from rest_framework import serializers

from .models import FolderPermission, FilePermission


class FolderPermissionGrantSerializer(serializers.Serializer):

    user_id = serializers.IntegerField()

    access_level = serializers.ChoiceField(
        choices=FolderPermission.AccessLevel.choices
    )


class FilePermissionGrantSerializer(serializers.Serializer):

    user_id = serializers.IntegerField()

    access_level = serializers.ChoiceField(
        choices=FilePermission.AccessLevel.choices
    )


class PermissionUpdateSerializer(serializers.Serializer):

    access_level = serializers.ChoiceField(
        choices=[
            ("VIEW", "View"),
            ("UPLOAD", "Upload"),
            ("DOWNLOAD", "Download"),
            ("EDIT", "Edit"),
            ("MANAGE", "Manage"),
        ]
    )


class FolderPermissionReadSerializer(serializers.ModelSerializer):

    user_username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    granted_by_username = serializers.SerializerMethodField()

    class Meta:
        model = FolderPermission

        fields = [
            "id",
            "folder_id",
            "user_id",
            "user_username",
            "access_level",
            "granted_by_username",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_granted_by_username(self, obj):

        if obj.granted_by:
            return obj.granted_by.username

        return None


class FilePermissionReadSerializer(serializers.ModelSerializer):

    user_username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    granted_by_username = serializers.SerializerMethodField()

    class Meta:
        model = FilePermission

        fields = [
            "id",
            "file_asset_id",
            "user_id",
            "user_username",
            "access_level",
            "granted_by_username",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_granted_by_username(self, obj):

        if obj.granted_by:
            return obj.granted_by.username

        return None