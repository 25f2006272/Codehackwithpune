from rest_framework import serializers

from .models import (
    Project,
    ProjectMembership,
    ProjectTask,
    ProjectDecision,
    
)


class ProjectCreateSerializer(serializers.ModelSerializer):

    workspace_id = serializers.IntegerField()

    class Meta:
        model = Project
        fields = [
            "workspace_id",
            "name",
            "description",
            "start_date",
            "target_end_date"
        ]

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Project name is required."
            )

        return value

    def validate(self, attrs):

        start = attrs.get("start_date")
        end = attrs.get("target_end_date")

        if start and end and end < start:
            raise serializers.ValidationError({
                "target_end_date":
                "Target end date cannot be before start date."
            })

        return attrs


class ProjectUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "status",
            "start_date",
            "target_end_date"
        ]

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Project name cannot be empty."
            )

        return value

    def validate(self, attrs):

        start = attrs.get(
            "start_date",
            self.instance.start_date
        )

        end = attrs.get(
            "target_end_date",
            self.instance.target_end_date
        )

        if start and end and end < start:
            raise serializers.ValidationError({
                "target_end_date":
                "Target end date cannot be before start date."
            })

        return attrs


class ProjectReadSerializer(serializers.ModelSerializer):

    workspace_name = serializers.CharField(
        source="workspace.name",
        read_only=True
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True
    )

    current_project_role = serializers.SerializerMethodField()

    member_count = serializers.IntegerField(read_only=True)

    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "name",
            "slug",
            "description",
            "status",
            "created_by_username",
            "current_project_role",
            "member_count",
            "task_count",
            "start_date",
            "target_end_date",
            "created_at",
            "updated_at"
        ]

    def get_current_project_role(self, obj):

        memberships = getattr(
            obj,
            "current_user_project_memberships",
            None
        )

        if memberships is None:
            return None

        return memberships[0].project_role if memberships else None


class ProjectMembershipReadSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = ProjectMembership
        fields = [
            "id",
            "user",
            "username",
            "email",
            "project_role",
            "status",
            "joined_at"
        ]


class AddProjectMemberSerializer(serializers.Serializer):

    user_id = serializers.IntegerField(min_value=1)

    project_role = serializers.ChoiceField(
        choices=[
            ("MEMBER", "Project Member"),
            ("VIEWER", "Project Viewer")
        ],
        default="MEMBER"
    )


class ChangeProjectRoleSerializer(serializers.Serializer):

    project_role = serializers.ChoiceField(
        choices=[
            ("MEMBER", "Project Member"),
            ("VIEWER", "Project Viewer")
        ]
    )


class SetProjectLeadSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField(min_value=1)


class EmptyRequestSerializer(serializers.Serializer):
    pass

# -------------------------------------------------
# TASK SERIALIZERS
# -------------------------------------------------

class ProjectTaskCreateSerializer(serializers.Serializer):

    title = serializers.CharField(max_length=250)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )

    assigned_to_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    priority = serializers.ChoiceField(
        choices=ProjectTask.Priority.choices,
        default=ProjectTask.Priority.MEDIUM
    )

    due_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    def validate_title(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Task title is required."
            )

        return value


class ProjectTaskUpdateSerializer(serializers.Serializer):

    title = serializers.CharField(
        max_length=250,
        required=False
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True
    )

    assigned_to_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    priority = serializers.ChoiceField(
        choices=ProjectTask.Priority.choices,
        required=False
    )

    status = serializers.ChoiceField(
        choices=ProjectTask.Status.choices,
        required=False
    )

    due_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    def validate_title(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Task title cannot be empty."
            )

        return value

    def validate(self, attrs):

        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )

        return attrs


class ProjectTaskReadSerializer(serializers.ModelSerializer):

    assigned_to_username = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
        allow_null=True
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True
    )

    class Meta:

        model = ProjectTask

        fields = [
            "id",
            "project",
            "title",
            "description",
            "assigned_to",
            "assigned_to_username",
            "created_by_username",
            "status",
            "priority",
            "due_date",
            "completed_at",
            "created_at",
            "updated_at"
        ]
        
        
# =================================================
# PROJECT DECISION SERIALIZERS
# =================================================


class ProjectDecisionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectDecision

        fields = [
            "title",
            "context",
            "decision",
            "rationale",
            "decision_type"
        ]

    def validate_title(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Decision title is required."
            )

        return value

    def validate_decision(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Decision description is required."
            )

        return value


class ProjectDecisionUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectDecision

        fields = [
            "title",
            "context",
            "decision",
            "rationale",
            "decision_type"
        ]

    def validate(self, attrs):

        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )

        return attrs

    def validate_title(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Decision title cannot be empty."
            )

        return value


class ProjectDecisionReadSerializer(serializers.ModelSerializer):

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = ProjectDecision

        fields = [
            "id",
            "project",
            "title",
            "context",
            "decision",
            "rationale",
            "decision_type",
            "status",
            "decision_date",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at"
        ]


class DecisionTransitionSerializer(serializers.Serializer):

    status = serializers.ChoiceField(
        choices=[
            (
                "ACCEPTED",
                "Accepted"
            ),
            (
                "REJECTED",
                "Rejected"
            ),
            (
                "SUPERSEDED",
                "Superseded"
            )
        ]
    )
    
