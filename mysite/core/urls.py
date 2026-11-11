from django.urls import path
from . import views

urlpatterns = [

    # Home
    path("", views.home, name="home"),

    # Personal Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("overview/", views.overview, name="overview"),
    path("activity/", views.activity, name="activity"),

    # Work
    path("projects/", views.projects, name="projects"),
    path("tasks/", views.tasks, name="tasks"),
    path("handovers/", views.handovers, name="handovers"),

    # Knowledge
    path("library/", views.library, name="library"),
    path("review-queue/", views.review_queue, name="review_queue"),
    path("ai-insights/", views.ai_insights, name="ai_insights"),

    # Workspaces
    path(
        "workspace-management/",
        views.workspace_management,
        name="workspace_management"
    ),
    path("ecometrics/", views.ecometrics, name="ecometrics"),
    path("research-group/", views.research_group, name="research_group"),

    # Settings and Support
    path("settings/", views.setting, name="setting"),
    path("help/", views.help, name="help"),
    
    path(
        "projects/<int:project_id>/",
        views.project_detail,
        name="project_detail",
    ),

]