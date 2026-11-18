from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import TransactionRecord
from .serializers import (
    TransactionRecordSerializer,
    ContractInfoSerializer,
    OnChainClaimSerializer,
)
from .soroban_client import soroban_service, SorobanClientException

class TransactionRecordListView(generics.ListAPIView):
    """
    List and filter on-chain Soroban and Stellar transaction records.
    """
    queryset = TransactionRecord.objects.all()
    serializer_class = TransactionRecordSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('tx_type', 'status', 'network', 'claim_reference')
    search_fields = ('tx_hash', 'claim_reference', 'contract_id')
    ordering_fields = ('created_at', 'ledger_sequence')

    @extend_schema(
        summary="List Stellar & Soroban transactions",
        description="Retrieve recorded blockchain transactions, hashes, ledger sequences, and explorer links."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class VerifyTransactionView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Verify transaction hash",
        description="Look up a transaction on Stellar / Soroban and verify its status.",
        responses={200: TransactionRecordSerializer}
    )
    def get(self, request, tx_hash):
        try:
            tx = TransactionRecord.objects.get(tx_hash=tx_hash)
            return Response(TransactionRecordSerializer(tx).data)
        except TransactionRecord.DoesNotExist:
            return Response(
                {"error": f"Transaction '{tx_hash}' not found in registry."},
                status=status.HTTP_404_NOT_FOUND
            )

class ContractInfoView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Soroban contract details",
        description="Retrieve deployed Soroban contract address, RPC URL, and network configuration.",
        responses={200: ContractInfoSerializer}
    )
    def get(self, request):
        info = soroban_service.get_contract_info()
        serializer = ContractInfoSerializer(info)
        return Response(serializer.data)

class ClaimOnChainStateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Query verified claim on-chain state",
        description="Reads verified claim state directly from the Soroban smart contract.",
        responses={200: OnChainClaimSerializer}
    )
    def get(self, request, claim_reference):
        try:
            state = soroban_service.get_claim(claim_reference)
            serializer = OnChainClaimSerializer(state)
            return Response(serializer.data)
        except SorobanClientException as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

