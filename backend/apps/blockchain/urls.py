from django.urls import path
from .views import (
    TransactionRecordListView,
    VerifyTransactionView,
    ContractInfoView,
    ClaimOnChainStateView,
)

urlpatterns = [
    path('transactions/', TransactionRecordListView.as_view(), name='blockchain-transactions'),
    path('transactions/<str:tx_hash>/', VerifyTransactionView.as_view(), name='blockchain-verify-tx'),
    path('contract-info/', ContractInfoView.as_view(), name='blockchain-contract-info'),
    path('claims/<str:claim_reference>/', ClaimOnChainStateView.as_view(), name='blockchain-claim-state'),
]

