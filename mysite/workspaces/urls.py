from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkspaceViewSet,
    MyInvitationsView,
    AcceptInvitationView,
    DeclineInvitationView
)


router = DefaultRouter()

router.register(
    "workspaces",
    WorkspaceViewSet,
    basename="workspace"
)


urlpatterns = [

    path(
        "invitations/",
        MyInvitationsView.as_view(),
        name="my-invitations"
    ),

    path(
        "invitations/<uuid:token>/accept/",
        AcceptInvitationView.as_view(),
        name="accept-invitation"
    ),

    path(
        "invitations/<uuid:token>/decline/",
        DeclineInvitationView.as_view(),
        name="decline-invitation"
    ),

    path("", include(router.urls)),
]