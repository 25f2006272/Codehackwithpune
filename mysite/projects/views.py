from django.db.models import Count, Q, Prefetch

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Project, ProjectMembership, ProjectTask, ProjectDecision
from . import services

from .serializers import (
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ProjectReadSerializer,
    ProjectMembershipReadSerializer,
    AddProjectMemberSerializer,
    ChangeProjectRoleSerializer,
    SetProjectLeadSerializer,
    EmptyRequestSerializer,
    ProjectTaskCreateSerializer,
    ProjectTaskUpdateSerializer,
    ProjectTaskReadSerializer,
    ProjectDecisionCreateSerializer,
    ProjectDecisionUpdateSerializer,
    ProjectDecisionReadSerializer,
    DecisionTransitionSerializer,
)


class ProjectViewSet(viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated]

    serializer_class = ProjectReadSerializer

    def get_queryset(self):

        user = self.request.user

        visible_projects = Project.objects.filter(
            Q(
                workspace__memberships__user=user,
                workspace__memberships__status="ACTIVE",
                workspace__memberships__role__in=[
                    "OWNER", "ADMIN", "VIEWER"
                ]
            )
            |
            Q(
                memberships__user=user,
                memberships__status="ACTIVE"
            )
        ).filter(
            workspace__status__in=["ACTIVE", "ARCHIVED"]
        )

        own_memberships = ProjectMembership.objects.filter(
            user=user,
            status=ProjectMembership.Status.ACTIVE
        )

        return (
            visible_projects
            .select_related("workspace", "created_by")
            .prefetch_related(
                Prefetch(
                    "memberships",
                    queryset=own_memberships,
                    to_attr="current_user_project_memberships"
                )
            )
            .annotate(
                member_count=Count(
                    "memberships",
                    filter=Q(
                        memberships__status="ACTIVE"
                    ),
                    distinct=True
                ),
                task_count=Count(
                    "tasks",
                    distinct=True
                )
            )
            .distinct()
        )

    def get_serializer_class(self):

        action = getattr(self, "action", None)

        if action == "create":
            return ProjectCreateSerializer

        if action == "partial_update":
            return ProjectUpdateSerializer

        if action == "members":

            if self.request.method == "POST":
                return AddProjectMemberSerializer

            return ProjectMembershipReadSerializer

        if action == "member_role":
            return ChangeProjectRoleSerializer

        if action == "set_lead":
            return SetProjectLeadSerializer

        if action in ["archive", "remove_member"]:
            return EmptyRequestSerializer
        
        if action == "tasks":

            if self.request.method == "POST":
                return ProjectTaskCreateSerializer

            return ProjectTaskReadSerializer

        if action == "task_detail":
            return ProjectTaskUpdateSerializer

        if action == "decisions":

            if self.request.method == "POST":
                return ProjectDecisionCreateSerializer

            return ProjectDecisionReadSerializer

        if action == "decision_detail":
            return ProjectDecisionUpdateSerializer

        if action == "decision_transition":
            return DecisionTransitionSerializer
        
        return ProjectReadSerializer

    # GET /api/v1/projects/
    def list(self, request):

        projects = self.get_queryset()

        serializer = ProjectReadSerializer(
            projects,
            many=True
        )

        return Response(serializer.data)

    # POST /api/v1/projects/
    def create(self, request):

        serializer = ProjectCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data.copy()

        workspace_id = data.pop("workspace_id")

        project = services.create_project(
            request.user,
            workspace_id,
            data,
            request=request
        )

        project = self.get_queryset().get(pk=project.pk)

        return Response(
            ProjectReadSerializer(project).data,
            status=status.HTTP_201_CREATED
        )

    # GET /api/v1/projects/<id>/
    def retrieve(self, request, pk=None):

        project = self.get_object()

        return Response(
            ProjectReadSerializer(project).data
        )

    # PATCH /api/v1/projects/<id>/
    def partial_update(self, request, pk=None):

        project = self.get_object()

        serializer = ProjectUpdateSerializer(
            project,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        project = services.update_project(
            request.user,
            project,
            serializer.validated_data,
            request=request
        )

        project = self.get_queryset().get(pk=project.pk)

        return Response(
            ProjectReadSerializer(project).data
        )

    # GET / POST /api/v1/projects/<id>/members/
    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):

        project = self.get_object()

        if request.method == "GET":

            services.get_project_access(
                request.user,
                project
            )

            members = ProjectMembership.objects.filter(
                project=project,
                status=ProjectMembership.Status.ACTIVE
            ).select_related("user")

            serializer = ProjectMembershipReadSerializer(
                members,
                many=True
            )

            return Response(serializer.data)

        serializer = AddProjectMemberSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        membership = services.add_project_member(
            request.user,
            project,
            serializer.validated_data["user_id"],
            serializer.validated_data["project_role"],
            request=request
        )

        return Response(
            ProjectMembershipReadSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )

    # PATCH /api/v1/projects/<id>/members/<membership_id>/role/
    @action(
        detail=True,
        methods=["patch"],
        url_path=r"members/(?P<membership_id>[^/.]+)/role"
    )
    def member_role(self, request, pk=None, membership_id=None):

        project = self.get_object()

        serializer = ChangeProjectRoleSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        membership = services.change_project_member_role(
            request.user,
            project,
            membership_id,
            serializer.validated_data["project_role"],
            request=request
        )

        return Response(
            ProjectMembershipReadSerializer(membership).data
        )

    # POST /api/v1/projects/<id>/set-lead/
    @action(detail=True, methods=["post"], url_path="set-lead")
    def set_lead(self, request, pk=None):

        project = self.get_object()

        serializer = SetProjectLeadSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        membership = services.set_project_lead(
            request.user,
            project,
            serializer.validated_data["membership_id"],
            request=request
        )

        return Response(
            ProjectMembershipReadSerializer(membership).data
        )

    # DELETE /api/v1/projects/<id>/members/<membership_id>/
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"members/(?P<membership_id>[^/.]+)"
    )
    def remove_member(self, request, pk=None, membership_id=None):

        project = self.get_object()

        services.remove_project_member(
            request.user,
            project,
            membership_id,
            request=request
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

    # POST /api/v1/projects/<id>/archive/
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):

        project = self.get_object()

        project = services.archive_project(
            request.user,
            project,
            request=request
        )

        return Response(
            ProjectReadSerializer(project).data
        )
        
        
    # -------------------------------------------------
    # GET / POST PROJECT TASKS
    # -------------------------------------------------

    @action(detail=True, methods=["get", "post"])
    def tasks(self, request, pk=None):

        project = self.get_object()

        if request.method == "GET":

            services.get_project_access(
                request.user,
                project
            )

            tasks = ProjectTask.objects.filter(
                project=project
            ).select_related(
                "assigned_to",
                "created_by"
            )

            serializer = ProjectTaskReadSerializer(
                tasks,
                many=True
            )

            return Response(serializer.data)

        serializer = ProjectTaskCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        task = services.create_project_task(
            request.user,
            project,
            serializer.validated_data,
            request=request
        )

        return Response(
            ProjectTaskReadSerializer(task).data,
            status=status.HTTP_201_CREATED
        )


    # -------------------------------------------------
    # PATCH PROJECT TASK
    # -------------------------------------------------

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"tasks/(?P<task_id>[^/.]+)"
    )
    def task_detail(self, request, pk=None, task_id=None):

        project = self.get_object()

        task = ProjectTask.objects.filter(
            pk=task_id,
            project=project
        ).first()

        if not task:
            return Response(
                {"detail": "Task not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProjectTaskUpdateSerializer(
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        task = services.update_project_task(
            request.user,
            task,
            serializer.validated_data,
            request=request
        )

        return Response(
            ProjectTaskReadSerializer(task).data
        )
        
    # =================================================
    # PROJECT DECISION APIs
    # =================================================


    # GET / POST PROJECT DECISIONS

    @action(detail=True, methods=["get", "post"])
    def decisions(self, request, pk=None):

        project = self.get_object()

        if request.method == "GET":

            services.get_project_access(
                request.user,
                project
            )

            decisions = ProjectDecision.objects.filter(
                project=project
            ).select_related(
                "created_by"
            )

            serializer = ProjectDecisionReadSerializer(
                decisions,
                many=True
            )

            return Response(serializer.data)

        serializer = ProjectDecisionCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        decision = services.create_project_decision(
            request.user,
            project,
            serializer.validated_data,
            request=request
        )

        return Response(
            ProjectDecisionReadSerializer(decision).data,
            status=status.HTTP_201_CREATED
        )


    # PATCH PROJECT DECISION

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"decisions/(?P<decision_id>[^/.]+)"
    )
    def decision_detail(self, request, pk=None, decision_id=None):

        project = self.get_object()

        decision = ProjectDecision.objects.filter(
            pk=decision_id,
            project=project
        ).first()

        if not decision:

            return Response(
                {"detail": "Decision not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProjectDecisionUpdateSerializer(
            decision,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        decision = services.update_project_decision(
            request.user,
            project,
            decision,
            serializer.validated_data,
            request=request
        )

        return Response(
            ProjectDecisionReadSerializer(decision).data
        )


    # TRANSITION DECISION STATUS

    @action(
        detail=True,
        methods=["post"],
        url_path=r"decisions/(?P<decision_id>[^/.]+)/transition"
    )
    def decision_transition(self, request, pk=None, decision_id=None):

        project = self.get_object()

        decision = ProjectDecision.objects.filter(
            pk=decision_id,
            project=project
        ).first()

        if not decision:

            return Response(
                {"detail": "Decision not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DecisionTransitionSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        decision = services.transition_project_decision(
            request.user,
            project,
            decision,
            serializer.validated_data["status"],
            request=request
        )

        return Response(
            ProjectDecisionReadSerializer(decision).data
        )