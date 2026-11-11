from rest_framework import serializers

from .models import Workspace, WorkspaceMembership, WorkspaceInvitation


class WorkspaceCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workspace
        fields = [
            "name",
            "description",
            "workspace_type",
            "logo_url"
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Workspace name is required.")

        return value


class WorkspaceUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workspace
        fields = [
            "name",
            "description",
            "workspace_type",
            "logo_url"
        ]

        extra_kwargs = {
            field: {"required": False}
            for field in fields
        }

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Workspace name cannot be empty.")

        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )

        return attrs


class WorkspaceReadSerializer(serializers.ModelSerializer):

    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True
    )

    current_user_role = serializers.SerializerMethodField()

    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "workspace_type",
            "logo_url",
            "owner_username",
            "current_user_role",
            "member_count",
            "status",
            "created_at",
            "updated_at"
        ]

    def get_current_user_role(self, obj):

        memberships = getattr(
            obj,
            "current_user_memberships",
            None
        )

        if memberships is not None:
            return memberships[0].role if memberships else None

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        membership = WorkspaceMembership.objects.filter(
            workspace=obj,
            user=request.user,
            status=WorkspaceMembership.Status.ACTIVE
        ).first()

        return membership.role if membership else None


class WorkspaceMembershipSerializer(serializers.ModelSerializer):

    user_id = serializers.IntegerField(read_only=True)

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True
    )

    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True
    )

    class Meta:
        model = WorkspaceMembership
        fields = [
            "id",
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "status",
            "joined_at"
        ]


class InviteMemberSerializer(serializers.Serializer):

    email = serializers.EmailField()

    invited_role = serializers.ChoiceField(
        choices=[
            ("ADMIN", "Workspace Admin"),
            ("MEMBER", "Member"),
            ("VIEWER", "Viewer")
        ],
        default="MEMBER"
    )

    def validate_email(self, value):
        return value.strip().lower()


class InvitationReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id",
            "email",
            "invited_role",
            "status",
            "expires_at",
            "created_at"
        ]


class InvitationCreatedSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id",
            "email",
            "invited_role",
            "status",
            "token",
            "expires_at"
        ]


class MyInvitationSerializer(serializers.ModelSerializer):

    workspace_name = serializers.CharField(
        source="workspace.name",
        read_only=True
    )

    workspace_slug = serializers.CharField(
        source="workspace.slug",
        read_only=True
    )

    invited_by_username = serializers.CharField(
        source="invited_by.username",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id",
            "workspace_name",
            "workspace_slug",
            "invited_by_username",
            "invited_role",
            "token",
            "expires_at",
            "created_at"
        ]


class ChangeMemberRoleSerializer(serializers.Serializer):

    role = serializers.ChoiceField(
        choices=[
            ("ADMIN", "Workspace Admin"),
            ("MEMBER", "Member"),
            ("VIEWER", "Viewer")
        ]
    )


class TransferOwnershipSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField(min_value=1)
    

class EmptyRequestSerializer(serializers.Serializer):
    pass