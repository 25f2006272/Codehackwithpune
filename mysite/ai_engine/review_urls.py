from django.urls import path

from .review_views import (
    KnowledgeItemDetailView,
    VerifyKnowledgeItemView,
    RejectKnowledgeItemView,
    ProjectConflictListView,
    KnowledgeConflictDetailView,
    ResolveKnowledgeConflictView,
)


urlpatterns = [
    path(
        "knowledge-items/<int:item_id>/",
        KnowledgeItemDetailView.as_view(),
        name="knowledge-item-detail",
    ),
    path(
        "knowledge-items/<int:item_id>/verify/",
        VerifyKnowledgeItemView.as_view(),
        name="knowledge-item-verify",
    ),
    path(
        "knowledge-items/<int:item_id>/reject/",
        RejectKnowledgeItemView.as_view(),
        name="knowledge-item-reject",
    ),
    path(
        "projects/<int:project_id>/conflicts/",
        ProjectConflictListView.as_view(),
        name="project-conflicts",
    ),
    path(
        "conflicts/<int:conflict_id>/",
        KnowledgeConflictDetailView.as_view(),
        name="knowledge-conflict-detail",
    ),
    path(
        "conflicts/<int:conflict_id>/resolve/",
        ResolveKnowledgeConflictView.as_view(),
        name="knowledge-conflict-resolve",
    ),
]
