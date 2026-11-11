from django.db.models import Count, Q, Prefetch

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Workspace, WorkspaceMembership
from . import services

from .serializers import (
    WorkspaceCreateSerializer,
    WorkspaceUpdateSerializer,
    WorkspaceReadSerializer,
    WorkspaceMembershipSerializer,
    InviteMemberSerializer,
    InvitationReadSerializer,
    InvitationCreatedSerializer,
    MyInvitationSerializer,
    ChangeMemberRoleSerializer,
    TransferOwnershipSerializer,
    EmptyRequestSerializer,
)


class WorkspaceViewSet(viewsets.GenericViewSet):
    serializer_class = WorkspaceReadSerializer

    def get_serializer_class(self):

        action = getattr(self, "action", None)

        if action in ["list", "create"]:
            return WorkspaceCreateSerializer

        if action in ["retrieve", "partial_update"]:
            return WorkspaceUpdateSerializer

        if action == "members":
            return WorkspaceMembershipSerializer

        if action == "invitations":
            if self.request.method == "POST":
                return InviteMemberSerializer

            return InvitationReadSerializer

        if action == "member_role":
            return ChangeMemberRoleSerializer

        if action == "transfer_ownership":
            return TransferOwnershipSerializer

        if action in [
            "archive",
            "leave",
            "remove_member",
            "revoke_invitation"
        ]:
            return EmptyRequestSerializer

        return WorkspaceReadSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        current_user_memberships = WorkspaceMembership.objects.filter(
            user=self.request.user,
            status=WorkspaceMembership.Status.ACTIVE
        )

        return (
            Workspace.objects.filter(
                memberships__user=self.request.user,
                memberships__status=WorkspaceMembership.Status.ACTIVE,
                status__in=[
                    Workspace.Status.ACTIVE,
                    Workspace.Status.ARCHIVED
                ]
            )
            .select_related("owner", "created_by")
            .prefetch_related(
                Prefetch(
                    "memberships",
                    queryset=current_user_memberships,
                    to_attr="current_user_memberships"
                )
            )
            .annotate(
                member_count=Count(
                    "memberships",
                    filter=Q(
                        memberships__status=WorkspaceMembership.Status.ACTIVE
                    ),
                    distinct=True
                )
            )
            .distinct()
        )

    def get_read_data(self, workspace):

        return WorkspaceReadSerializer(
            workspace,
            context={"request": self.request}
        ).data

    # GET /api/v1/workspaces/
    def list(self, request):

        queryset = self.get_queryset()

        return Response(
            WorkspaceReadSerializer(
                queryset,
                many=True,
                context={"request": request}
            ).data
        )

    # GET /api/v1/workspaces/<id>/
    def retrieve(self, request, pk=None):

        workspace = self.get_object()

        return Response(self.get_read_data(workspace))

    # POST /api/v1/workspaces/
    def create(self, request):

        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace = services.create_workspace(
            request.user,
            serializer.validated_data,
            request=request
        )

        workspace = self.get_queryset().get(pk=workspace.pk)

        return Response(
            self.get_read_data(workspace),
            status=status.HTTP_201_CREATED
        )

    # PATCH /api/v1/workspaces/<id>/
    def partial_update(self, request, pk=None):

        workspace = self.get_object()

        serializer = WorkspaceUpdateSerializer(
            workspace,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)

        workspace = services.update_workspace(
            request.user,
            workspace,
            serializer.validated_data,
            request=request
        )

        workspace = self.get_queryset().get(pk=workspace.pk)

        return Response(self.get_read_data(workspace))

    # GET /api/v1/workspaces/<id>/members/
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):

        workspace = self.get_object()

        queryset = WorkspaceMembership.objects.filter(
            workspace=workspace,
            status=WorkspaceMembership.Status.ACTIVE
        ).select_related("user").order_by("joined_at")

        serializer = WorkspaceMembershipSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    # GET/POST /api/v1/workspaces/<id>/invitations/
    @action(detail=True, methods=["get", "post"])
    def invitations(self, request, pk=None):

        workspace = self.get_object()

        if request.method == "GET":

            invitations = services.get_workspace_invitations(
                request.user,
                workspace
            )

            serializer = InvitationReadSerializer(
                invitations,
                many=True
            )

            return Response(serializer.data)

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invitation = services.invite_member(
            request.user,
            workspace,
            serializer.validated_data["email"],
            serializer.validated_data["invited_role"],
            request=request
        )

        return Response(
            InvitationCreatedSerializer(invitation).data,
            status=status.HTTP_201_CREATED
        )

    # PATCH /api/v1/workspaces/<id>/members/<member_id>/role/
    @action(
        detail=True,
        methods=["patch"],
        url_path=r"members/(?P<membership_id>[^/.]+)/role"
    )
    def member_role(self, request, pk=None, membership_id=None):

        workspace = self.get_object()

        serializer = ChangeMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = services.change_member_role(
            request.user,
            workspace,
            membership_id,
            serializer.validated_data["role"],
            request=request
        )

        return Response(
            WorkspaceMembershipSerializer(membership).data
        )

    # DELETE /api/v1/workspaces/<id>/members/<member_id>/
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"members/(?P<membership_id>[^/.]+)"
    )
    def remove_member(self, request, pk=None, membership_id=None):

        workspace = self.get_object()

        services.remove_member(
            request.user,
            workspace,
            membership_id,
            request=request
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /api/v1/workspaces/<id>/transfer-ownership/
    @action(detail=True, methods=["post"], url_path="transfer-ownership")
    def transfer_ownership(self, request, pk=None):

        workspace = self.get_object()

        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace = services.transfer_ownership(
            request.user,
            workspace,
            serializer.validated_data["membership_id"],
            request=request
        )

        workspace = self.get_queryset().get(pk=workspace.pk)

        return Response(self.get_read_data(workspace))

    # POST /api/v1/workspaces/<id>/archive/
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):

        workspace = self.get_object()

        workspace = services.archive_workspace(
            request.user,
            workspace,
            request=request
        )

        workspace = self.get_queryset().get(pk=workspace.pk)

        return Response(self.get_read_data(workspace))

    # POST /api/v1/workspaces/<id>/leave/
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):

        workspace = self.get_object()

        services.leave_workspace(
            request.user,
            workspace,
            request=request
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /api/v1/workspaces/<id>/invitations/<invitation_id>/revoke/
    @action(
        detail=True,
        methods=["post"],
        url_path=r"invitations/(?P<invitation_id>[^/.]+)/revoke"
    )
    def revoke_invitation(self, request, pk=None, invitation_id=None):

        workspace = self.get_object()

        services.revoke_invitation(
            request.user,
            workspace,
            invitation_id,
            request=request
        )

        return Response(
            {"detail": "Invitation revoked successfully."}
        )


class MyInvitationsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        invitations = services.get_my_invitations(request.user)

        serializer = MyInvitationSerializer(
            invitations,
            many=True
        )

        return Response(serializer.data)


class AcceptInvitationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, token):

        membership = services.accept_invitation(
            request.user,
            token,
            request=request
        )

        return Response(
            WorkspaceMembershipSerializer(membership).data,
            status=status.HTTP_200_OK
        )


class DeclineInvitationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, token):

        services.decline_invitation(
            request.user,
            token,
            request=request
        )

        return Response(
            {"detail": "Invitation declined successfully."},
            status=status.HTTP_200_OK
        )