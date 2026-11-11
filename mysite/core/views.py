from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone



from django.http import Http404

from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

from workspaces.models import Workspace, WorkspaceMembership

from filemanager.models import Folder, FilePermission, FileAsset

from filemanager.services import (
    list_workspace_folders,
    get_folder_for_user,
    require_folder_access,
)

from filemanager.file_services import list_workspace_files


from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from ai_engine.models import KnowledgeItem
from workspaces.models import WorkspaceInvitation

from accounts.models import UserProfile
from workspaces.models import Workspace, WorkspaceMembership
from projects.models import (
    Project,
    ProjectMembership,
    ProjectTask,
    ProjectActivity,
    ProjectDecision,
)
from handover.models import Handover


from projects import services as project_services
from django.shortcuts import get_object_or_404


# ==========================================
# PUBLIC HOME PAGE
# ==========================================

def home(request):
    return render(request, "home.html")


# ==========================================
# DASHBOARD
# ==========================================

@login_required
def dashboard(request):

    user = request.user

    # Logged-in user's profile
    profile = UserProfile.objects.filter(
        user=user
    ).only("display_name").first()

    display_name = (
        profile.display_name.strip()
        if profile and profile.display_name
        else user.get_full_name().strip() or user.username
    )

    first_name = (
        user.first_name.strip()
        or display_name.split()[0]
    )

    # Greeting based on local time
    current_hour = timezone.localtime().hour

    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # --------------------------------------
    # 1. USER WORKSPACES
    # --------------------------------------

    workspace_memberships = (
        WorkspaceMembership.objects
        .filter(
            user=user,
            status="ACTIVE"
        )
        .select_related("workspace")
    )

    # Include workspaces owned by the user
    workspace_map = {
        workspace.id: workspace
        for workspace in Workspace.objects.filter(owner=user)
    }

    # Include workspaces where user is a member
    for membership in workspace_memberships:
        workspace_map[membership.workspace_id] = (
            membership.workspace
        )

    workspaces = list(workspace_map.values())

    workspace_ids = [
        workspace.id for workspace in workspaces
    ]

    workspace_count = len(workspaces)

    # --------------------------------------
    # 2. USER PROJECTS
    # --------------------------------------

    workspace_project_ids = Project.objects.filter(
        workspace_id__in=workspace_ids
    ).values_list("id", flat=True)

    membership_project_ids = ProjectMembership.objects.filter(
        user=user,
        status="ACTIVE"
    ).values_list("project_id", flat=True)

    project_ids = set(workspace_project_ids)
    project_ids.update(membership_project_ids)

    projects_queryset = (
        Project.objects
        .filter(id__in=project_ids)
        .select_related("workspace")
        .order_by("-updated_at")
    )

    project_count = projects_queryset.count()

    # --------------------------------------
    # 3. WORKSPACE DETAILS
    # --------------------------------------

    workspaces_data = []

    for workspace in workspaces:

        member_count = WorkspaceMembership.objects.filter(
            workspace=workspace,
            status="ACTIVE"
        ).count()

        workspace_projects_count = Project.objects.filter(
            workspace=workspace
        ).count()

        workspaces_data.append({
            "workspace": workspace,
            "member_count": member_count,
            "project_count": workspace_projects_count,
        })

    # --------------------------------------
    # 4. USER TASKS
    # --------------------------------------

    tasks_queryset = (
        ProjectTask.objects
        .filter(
            assigned_to=user,
            project_id__in=project_ids
        )
        .exclude(status="CANCELLED")
        .select_related("project")
        .order_by("-updated_at")
    )

    task_count = tasks_queryset.count()

    recent_tasks = tasks_queryset[:3]

    # --------------------------------------
    # 5. RECENT PROJECT ACTIVITY
    # --------------------------------------

    recent_activities = (
        ProjectActivity.objects
        .filter(project_id__in=project_ids)
        .select_related("project", "actor")
        .order_by("-created_at")[:5]
    )

    # --------------------------------------
    # 6. HANDOVERS
    # --------------------------------------

    handovers_queryset = (
        Handover.objects
        .filter(
            Q(project_id__in=project_ids)
            | Q(departing_member=user)
            | Q(incoming_member=user)
        )
        .select_related(
            "project",
            "departing_member",
            "incoming_member"
        )
        .order_by("-updated_at")
        .distinct()
    )

    handover_count = handovers_queryset.filter(
        status__in=[
            "PROCESSING",
            "IN_REVIEW",
            "CHANGES_REQUESTED",
            "APPROVED",
            "SHARED",
        ]
    ).count()

    recent_handovers = handovers_queryset[:3]

    # --------------------------------------
    # 7. DASHBOARD CONTEXT
    # --------------------------------------

    context = {

        "display_name": display_name,
        "first_name": first_name,
        "greeting": greeting,

        "workspace_count": workspace_count,
        "project_count": project_count,
        "task_count": task_count,
        "handover_count": handover_count,

        "workspaces_data": workspaces_data,
        "recent_tasks": recent_tasks,
        "recent_activities": recent_activities,
        "recent_handovers": recent_handovers,

    }

    return render(
        request,
        "dashboard.html",
        context
    )


# ==========================================
# OTHER DASHBOARD PAGES
# ==========================================

@login_required
def overview(request):

    user = request.user
    today = timezone.localdate()

    # ======================================
    # DATE AND GREETING
    # ======================================

    current_hour = timezone.localtime().hour

    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    profile = UserProfile.objects.filter(
        user=user
    ).only("display_name").first()

    display_name = (
        profile.display_name.strip()
        if profile and profile.display_name
        else user.get_full_name().strip() or user.username
    )

    first_name = (
        user.first_name.strip()
        or display_name.split()[0]
    )

    # ======================================
    # WORKSPACES
    # ======================================

    memberships = (
        WorkspaceMembership.objects
        .filter(user=user, status="ACTIVE")
        .select_related("workspace")
    )

    workspace_map = {
        membership.workspace_id: membership.workspace
        for membership in memberships
    }

    owned_workspaces = Workspace.objects.filter(
        owner=user,
        status="ACTIVE"
    )

    for workspace in owned_workspaces:
        workspace_map[workspace.id] = workspace

    workspaces = list(workspace_map.values())

    workspace_ids = [
        workspace.id for workspace in workspaces
    ]

    workspace_count = len(workspaces)

    # Pending invitations
    invited_count = WorkspaceInvitation.objects.filter(
        email__iexact=user.email,
        status="PENDING",
        expires_at__gt=timezone.now()
    ).count() if user.email else 0

    # Workspace member/project counts
    workspaces_data = []

    for workspace in workspaces:

        member_count = WorkspaceMembership.objects.filter(
            workspace=workspace,
            status="ACTIVE"
        ).count()

        project_count_for_workspace = Project.objects.filter(
            workspace=workspace
        ).count()

        workspaces_data.append({
            "workspace": workspace,
            "member_count": member_count,
            "project_count": project_count_for_workspace,
        })

    # ======================================
    # PROJECTS
    # ======================================

    workspace_project_ids = Project.objects.filter(
        workspace_id__in=workspace_ids
    ).values_list("id", flat=True)

    membership_project_ids = ProjectMembership.objects.filter(
        user=user,
        status="ACTIVE"
    ).values_list("project_id", flat=True)

    project_ids = set(workspace_project_ids)
    project_ids.update(membership_project_ids)

    projects_queryset = (
        Project.objects
        .filter(id__in=project_ids)
        .select_related("workspace")
        .order_by("-updated_at")
    )

    project_count = projects_queryset.count()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    updated_project_count = projects_queryset.filter(
        updated_at__date__gte=week_start,
        updated_at__date__lte=week_end
    ).count()

    # ======================================
    # TASKS
    # ======================================

    tasks_queryset = (
        ProjectTask.objects
        .filter(
            assigned_to=user,
            project_id__in=project_ids,
            status__in=[
                "TODO",
                "IN_PROGRESS",
                "BLOCKED"
            ]
        )
        .select_related("project", "project__workspace")
        .order_by("due_date", "-created_at")
    )

    open_task_count = tasks_queryset.count()

    due_this_week_count = tasks_queryset.filter(
        due_date__gte=today,
        due_date__lte=week_end
    ).count()

    overdue_task_count = tasks_queryset.filter(
        due_date__lt=today
    ).count()

    focus_tasks = tasks_queryset[:3]

    # ======================================
    # PENDING KNOWLEDGE REVIEWS
    # ======================================

    pending_review_count = KnowledgeItem.objects.filter(
        project_id__in=project_ids,
        verification_status="NEEDS_REVIEW"
    ).count()

    # ======================================
    # RECENT ACTIVITY
    # ======================================

    recent_activities = (
        ProjectActivity.objects
        .filter(project_id__in=project_ids)
        .select_related("project", "actor")
        .order_by("-created_at")[:5]
    )

    # ======================================
    # PROJECT HEALTH / PROGRESS
    # ======================================

    project_progress = []

    for project in projects_queryset[:5]:

        task_stats = ProjectTask.objects.filter(
            project=project
        ).exclude(
            status="CANCELLED"
        ).aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(status="DONE")
            )
        )

        total_tasks = task_stats["total"]
        completed_tasks = task_stats["completed"]

        progress = (
            round((completed_tasks / total_tasks) * 100)
            if total_tasks else 0
        )

        project_progress.append({
            "project": project,
            "progress": progress,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
        })

    # ======================================
    # TEMPLATE CONTEXT
    # ======================================

    context = {
        "display_name": display_name,
        "first_name": first_name,
        "greeting": greeting,

        "workspace_count": workspace_count,
        "invited_count": invited_count,

        "project_count": project_count,
        "updated_project_count": updated_project_count,

        "open_task_count": open_task_count,
        "due_this_week_count": due_this_week_count,
        "overdue_task_count": overdue_task_count,

        "pending_review_count": pending_review_count,

        "workspaces_data": workspaces_data,
        "recent_activities": recent_activities,
        "focus_tasks": focus_tasks,
        "project_progress": project_progress,
    }

    return render(request, "overview.html", context)



@login_required
def activity(request):
    return render(request, "activity.html")


@login_required
def projects(request):

    user = request.user

    # Projects accessible to the logged-in user
    projects_list = (
        Project.objects.filter(
            Q(
                workspace__memberships__user=user,
                workspace__memberships__status="ACTIVE",
                workspace__memberships__role__in=[
                    "OWNER",
                    "ADMIN",
                    "VIEWER",
                ],
            )
            |
            Q(
                memberships__user=user,
                memberships__status="ACTIVE",
            )
        )
        .filter(
            workspace__status__in=["ACTIVE", "ARCHIVED"]
        )
        .select_related(
            "workspace",
            "created_by",
        )
        .annotate(
            member_count=Count(
                "memberships",
                filter=Q(memberships__status="ACTIVE"),
                distinct=True,
            ),
            total_task_count=Count(
                "tasks",
                filter=~Q(tasks__status="CANCELLED"),
                distinct=True,
            ),
            completed_task_count=Count(
                "tasks",
                filter=Q(tasks__status="DONE"),
                distinct=True,
            ),
        )
        .distinct()
        .order_by("-created_at")
    )

    # Calculate project progress
    for project in projects_list:

        if project.total_task_count > 0:
            project.progress_percentage = round(
                (
                    project.completed_task_count
                    / project.total_task_count
                ) * 100
            )
        else:
            project.progress_percentage = 0

    # Project statistics
    total_projects = projects_list.count()

    in_progress_count = projects_list.filter(
        status=Project.Status.ACTIVE
    ).count()

    planning_count = projects_list.filter(
        status=Project.Status.PLANNING
    ).count()

    completed_count = projects_list.filter(
        status=Project.Status.COMPLETED
    ).count()

    # IN_REVIEW is not currently available in Project.Status
    in_review_count = 0

    # Workspaces where the current user can create projects
    available_workspaces = Workspace.objects.filter(
        Q(owner=user)
        |
        Q(
            memberships__user=user,
            memberships__status="ACTIVE",
            memberships__role__in=["OWNER", "ADMIN"],
        ),
        status=Workspace.Status.ACTIVE,
    ).distinct()
    
    context = {
        "projects": projects_list,
        "total_projects": total_projects,
        "in_progress_count": in_progress_count,
        "in_review_count": in_review_count,
        "completed_count": completed_count,
        "planning_count": planning_count,
        "available_workspaces": available_workspaces,
    }

    return render(
        request,
        "projects.html",
        context
    )


@login_required
def project_detail(request, project_id):

    user = request.user

    # Find only projects accessible to the logged-in user
    project = get_object_or_404(
        Project.objects.filter(
            Q(
                workspace__memberships__user=user,
                workspace__memberships__status="ACTIVE",
                workspace__memberships__role__in=[
                    "OWNER",
                    "ADMIN",
                    "VIEWER",
                ],
            )
            |
            Q(
                memberships__user=user,
                memberships__status="ACTIVE",
            )
        )
        .filter(
            workspace__status__in=["ACTIVE", "ARCHIVED"]
        )
        .select_related("workspace", "created_by")
        .distinct(),
        pk=project_id,
    )

    # Enforce project-level access rules
    project_services.get_project_access(user, project)

    members = (
        ProjectMembership.objects
        .filter(
            project=project,
            status="ACTIVE",
        )
        .select_related("user")
        .order_by("joined_at")
    )

    tasks_list = (
        ProjectTask.objects
        .filter(project=project)
        .select_related("assigned_to", "created_by")
        .order_by("-created_at")
    )

    decisions = (
        ProjectDecision.objects
        .filter(project=project)
        .select_related("created_by")
        .order_by("-created_at")
    )

    activities = (
        ProjectActivity.objects
        .filter(project=project)
        .select_related("actor")
        .order_by("-created_at")[:20]
    )

    total_tasks = tasks_list.exclude(
        status="CANCELLED"
    ).count()

    completed_tasks = tasks_list.filter(
        status="DONE"
    ).count()

    progress = (
        round(completed_tasks / total_tasks * 100)
        if total_tasks else 0
    )

    current_membership = members.filter(
        user=user
    ).first()

    context = {
        "project": project,
        "members": members,
        "tasks": tasks_list,
        "decisions": decisions,
        "activities": activities,
        "current_membership": current_membership,

        "member_count": members.count(),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress": progress,

        "open_tasks": tasks_list.filter(
            status__in=["TODO", "IN_PROGRESS", "BLOCKED"]
        ).count(),
    }

    return render(
        request,
        "project_detail.html",
        context,
    )

@login_required
def tasks(request):
    return render(request, "tasks.html")


@login_required
def handovers(request):
    return render(request, "handovers.html")


@login_required
def library(request):

    user = request.user

    # ======================================
    # ACCESSIBLE WORKSPACES
    # ======================================

    workspaces = (
        Workspace.objects
        .filter(status="ACTIVE")
        .filter(
            Q(owner=user)
            | Q(
                memberships__user=user,
                memberships__status="ACTIVE"
            )
        )
        .distinct()
        .order_by("name")
    )

    workspace_id = request.GET.get("workspace")

    workspace = None

    if workspace_id and workspace_id.isdigit():
        workspace = workspaces.filter(
            id=int(workspace_id)
        ).first()

    if workspace is None:
        workspace = workspaces.first()

    # ======================================
    # DEFAULT LIBRARY DATA
    # ======================================

    current_folder = None
    folders = []
    files = []

    workspace_members = []

    can_manage_permissions = False
    current_membership = None

    search_query = request.GET.get(
        "search", ""
    ).strip()

    shared_file_count = 0

    # ======================================
    # SELECTED WORKSPACE CONTENT
    # ======================================

    if workspace:

        # ----------------------------------
        # CURRENT USER MEMBERSHIP
        # ----------------------------------

        current_membership = (
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                user=user,
                status="ACTIVE"
            ).first()
        )

        # ----------------------------------
        # PERMISSION MANAGEMENT ACCESS
        # ----------------------------------

        can_manage_permissions = (
            workspace.owner_id == user.id
            or (
                current_membership is not None
                and current_membership.role in [
                    WorkspaceMembership.Role.OWNER,
                    WorkspaceMembership.Role.ADMIN,
                ]
            )
        )

        # ----------------------------------
        # ACTIVE WORKSPACE MEMBERS
        # ----------------------------------

        workspace_members = (
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                status="ACTIVE"
            )
            .select_related("user")
            .exclude(user=user)
            .order_by("user__username")
        )

        # ----------------------------------
        # OPEN SELECTED FOLDER
        # ----------------------------------

        folder_id = request.GET.get("folder")

        if folder_id:

            try:
                folder_id = int(folder_id)

            except (TypeError, ValueError):
                raise Http404("Invalid folder.")

            current_folder = get_folder_for_user(
                user,
                folder_id
            )

            if current_folder.workspace_id != workspace.id:
                raise Http404("Folder not found.")

        # ----------------------------------
        # FOLDERS
        # ----------------------------------

        folder_queryset = list_workspace_folders(
            user=user,
            workspace=workspace,
            parent_id=(
                current_folder.id
                if current_folder
                else None
            ),
            search=search_query or None
        )

        # Filter folders according to actual VIEW permission
        for folder in folder_queryset:

            try:

                require_folder_access(
                    user,
                    folder,
                    "VIEW"
                )

                folders.append(folder)

            except DRFPermissionDenied:
                continue

        # ----------------------------------
        # FILES
        # ----------------------------------

        files = list_workspace_files(
            user=user,
            workspace=workspace,
            folder=current_folder,
            search=search_query or None
        )

        # ----------------------------------
        # SHARED FILE COUNT
        # ----------------------------------

        shared_file_count = FilePermission.objects.filter(
            user=user,
            is_active=True,
            file_asset__workspace=workspace,
            file_asset__status="ACTIVE"
        ).count()

    # ======================================
    # BREADCRUMB
    # ======================================

    breadcrumbs = []

    parent = current_folder

    while parent:

        breadcrumbs.insert(0, parent)

        parent = parent.parent

    # ======================================
    # LIBRARY STATISTICS
    # ======================================

    file_count = len(files)
    folder_count = len(folders)

    total_resources = file_count + folder_count

    document_count = sum(
        1 for file_asset in files
        if file_asset.current_version
    )

    # ======================================
    # TEMPLATE CONTEXT
    # ======================================

    context = {

        "workspaces": workspaces,
        "workspace": workspace,

        "current_folder": current_folder,
        "breadcrumbs": breadcrumbs,

        "folders": folders,
        "files": files,

        "workspace_members": workspace_members,

        "current_membership": current_membership,
        "can_manage_permissions": can_manage_permissions,

        "search_query": search_query,

        "total_resources": total_resources,
        "document_count": document_count,
        "folder_count": folder_count,
        "shared_file_count": shared_file_count,

    }

    return render(
        request,
        "library.html",
        context
    )


@login_required
def review_queue(request):
    return render(request, "review_queue.html")


@login_required
def ai_insights(request):
    return render(request, "ai_insights.html")


# ==========================================
# WORKSPACE PAGES
# ==========================================

@login_required
def workspace_management(request):

    user = request.user

    # 1. Workspaces where the logged-in user is owner or active member
    workspaces = (
        Workspace.objects.filter(status="ACTIVE")
        .filter(
            Q(owner=user)
            | Q(
                memberships__user=user,
                memberships__status="ACTIVE"
            )
        )
        .distinct()
        .order_by("name")
    )

    # 2. Get selected workspace from URL
    workspace_id = request.GET.get("workspace")

    workspace = None

    if workspace_id and workspace_id.isdigit():
        workspace = workspaces.filter(
            id=int(workspace_id)
        ).first()

    # Default to the first accessible workspace
    if workspace is None:
        workspace = workspaces.first()

    # 3. Default context
    context = {
        "workspaces": workspaces,
        "workspace": workspace,

        # Members
        "memberships": [],
        "member_count": 0,
        "current_membership": None,

        # Member management permissions
        "can_manage_members": False,
        "can_invite_admin": False,

        # Projects
        "project_list": [],
        "project_count": 0,
        "in_progress_project_count": 0,

        # Tasks
        "open_task_count": 0,
        "due_this_week_count": 0,

        # Files and folders
        "file_list": [],
        "file_count": 0,
        "folder_count": 0,
        "shared_file_count": 0,

        # Invitations
        "pending_invitations": [],
        "pending_invitation_count": 0,
    }

    if workspace:

        # 4. Workspace Members
        memberships = (
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                status="ACTIVE"
            )
            .select_related("user")
            .order_by("joined_at")
        )

        # Current logged-in user's membership
        current_membership = memberships.filter(
            user=user
        ).first()

        # Member management permissions
        current_role = (
            current_membership.role
            if current_membership
            else None
        )

        can_manage_members = current_role in [
            WorkspaceMembership.Role.OWNER,
            WorkspaceMembership.Role.ADMIN,
        ]

        can_invite_admin = (
            current_role == WorkspaceMembership.Role.OWNER
        )

        # 5. Workspace Projects
        projects = (
            Project.objects.filter(workspace=workspace)
            .exclude(status="ARCHIVED")
            .order_by("-updated_at")
        )

        # 6. Workspace Tasks
        tasks = ProjectTask.objects.filter(
            project__workspace=workspace
        ).exclude(
            status__in=["DONE", "CANCELLED"]
        )

        today = timezone.localdate()
        week_end = today + timedelta(days=7)

        # 7. Workspace Files
        workspace_files = (
            FileAsset.objects.filter(
                workspace=workspace,
                status="ACTIVE"
            )
            .select_related(
                "current_version",
                "created_by"
            )
            .order_by("-updated_at")
        )

        # 8. Workspace Folders
        workspace_folders = Folder.objects.filter(
            workspace=workspace,
            is_archived=False
        )

        # 9. Pending Invitations
        pending_invitations = (
            WorkspaceInvitation.objects.filter(
                workspace=workspace,
                status="PENDING",
                expires_at__gt=timezone.now()
            )
            .select_related("invited_by")
            .order_by("-created_at")
        )

        # 10. Files having direct permissions
        shared_file_count = (
            FilePermission.objects.filter(
                file_asset__workspace=workspace,
                file_asset__status="ACTIVE",
                is_active=True
            )
            .values("file_asset_id")
            .distinct()
            .count()
        )

        # 11. Update template context
        context.update({

            # Members
            "memberships": memberships,
            "member_count": memberships.count(),
            "current_membership": current_membership,

            # Management permissions
            "can_manage_members": can_manage_members,
            "can_invite_admin": can_invite_admin,

            # Projects
            "project_list": projects,
            "project_count": projects.count(),
            "in_progress_project_count": projects.filter(
                status="ACTIVE"
            ).count(),

            # Tasks
            "open_task_count": tasks.count(),
            "due_this_week_count": tasks.filter(
                due_date__gte=today,
                due_date__lte=week_end
            ).count(),

            # Files and folders
            "file_list": workspace_files,
            "file_count": workspace_files.count(),
            "folder_count": workspace_folders.count(),
            "shared_file_count": shared_file_count,

            # Invitations
            "pending_invitations": pending_invitations,
            "pending_invitation_count": pending_invitations.count(),

        })

    return render(
        request,
        "workspace_management.html",
        context
    )


@login_required
def ecometrics(request):
    return render(request, "ecometrics.html")


@login_required
def research_group(request):
    return render(request, "research_group.html")


# ==========================================
# SETTINGS AND SUPPORT
# ==========================================

@login_required
def setting(request):
    return render(request, "settings.html")


@login_required
def help(request):
    return render(request, "help.html")