from django.urls import path
from .views import (
    ProjectHandoverListCreateView,
    HandoverDetailView,
    HandoverItemsView,
    HandoverItemDetailView,
    HandoverSubmitView,
    HandoverVersionsView,
    HandoverReviewView,
    HandoverShareView,
    HandoverAcknowledgementView,
)

urlpatterns = [
    path("projects/<int:project_id>/handovers/", ProjectHandoverListCreateView.as_view(), name="project-handovers"),
    path("handovers/<int:handover_id>/", HandoverDetailView.as_view(), name="handover-detail"),
    path("handovers/<int:handover_id>/items/", HandoverItemsView.as_view(), name="handover-items"),
    path("handover-items/<int:item_id>/", HandoverItemDetailView.as_view(), name="handover-item-detail"),
    path("handovers/<int:handover_id>/submit/", HandoverSubmitView.as_view(), name="handover-submit"),
    path("handovers/<int:handover_id>/versions/", HandoverVersionsView.as_view(), name="handover-versions"),
    path("handovers/<int:handover_id>/review/", HandoverReviewView.as_view(), name="handover-review"),
    path("handovers/<int:handover_id>/share/", HandoverShareView.as_view(), name="handover-share"),
    path("handovers/<int:handover_id>/acknowledgement/", HandoverAcknowledgementView.as_view(), name="handover-acknowledgement"),
]
