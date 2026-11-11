from django.urls import path

from .views import (
    DocumentExtractionView,
    DocumentChunkListView,
)

from .reconstruction_views import (
    ProjectAnalysisView,
    ProjectKnowledgeListView,
    ProjectAnalysisRunListView,
)
from .review_urls import urlpatterns as review_urlpatterns


urlpatterns = [

    path(
        "files/<int:file_id>/extract/",
        DocumentExtractionView.as_view(),
        name="document-extraction",
    ),

    path(
        "extractions/<int:extraction_id>/chunks/",
        DocumentChunkListView.as_view(),
        name="document-chunks",
    ),
    
    path(
        "projects/<int:project_id>/analyze/",
        ProjectAnalysisView.as_view(),
        name="project-ai-analysis",
    ),

    path(
        "projects/<int:project_id>/knowledge/",
        ProjectKnowledgeListView.as_view(),
        name="project-knowledge-list",
    ),

    path(
        "projects/<int:project_id>/analysis-runs/",
        ProjectAnalysisRunListView.as_view(),
        name="project-analysis-runs",
    ),

]

urlpatterns += review_urlpatterns