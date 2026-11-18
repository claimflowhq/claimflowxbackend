from django.urls import path
from .views import (
    PayoutAuthorizationListView,
    PayoutAuthorizationDetailView,
    PendingPayoutClaimsView,
)

urlpatterns = [
    path('', PayoutAuthorizationListView.as_view(), name='payout-list'),
    path('<int:pk>/', PayoutAuthorizationDetailView.as_view(), name='payout-detail'),
    path('pending-claims/', PendingPayoutClaimsView.as_view(), name='payout-pending-claims'),
]

