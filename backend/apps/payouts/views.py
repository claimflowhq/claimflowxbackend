from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.claims.models import PayoutAuthorization, Claim, ClaimStatus
from apps.claims.serializers import PayoutAuthorizationSerializer, ClaimSerializer
from apps.authentication.permissions import IsReviewerOrAdmin

class PayoutAuthorizationListView(generics.ListAPIView):
    """
    List of all authorized payouts, with claimant, authorized amounts, status, and transaction hashes.
    """
    queryset = PayoutAuthorization.objects.all().select_related('claim', 'authorized_by', 'claim__claimant')
    serializer_class = PayoutAuthorizationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('status', 'claim__category')
    search_fields = ('claim__claim_reference', 'tx_hash', 'settlement_reference', 'authorized_by__username')
    ordering_fields = ('created_at', 'amount')

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PayoutAuthorization.objects.none()
        if user.is_reviewer or user.is_admin_user:
            return PayoutAuthorization.objects.all()
        return PayoutAuthorization.objects.filter(claim__claimant=user)

    @extend_schema(
        summary="List payout authorizations",
        description="View records of authorized payouts, on-chain transaction hashes, and settlement statuses."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class PayoutAuthorizationDetailView(generics.RetrieveAPIView):
    queryset = PayoutAuthorization.objects.all().select_related('claim', 'authorized_by')
    serializer_class = PayoutAuthorizationSerializer
    permission_classes = (permissions.IsAuthenticated,)

class PendingPayoutClaimsView(APIView):
    permission_classes = (IsReviewerOrAdmin,)

    @extend_schema(
        summary="Approved claims awaiting payout authorization",
        description="Returns list of approved claims ready for payout authorization on Soroban.",
        responses={200: ClaimSerializer(many=True)}
    )
    def get(self, request):
        approved_claims = Claim.objects.filter(
            status=ClaimStatus.APPROVED,
            payout_authorization__isnull=True
        ).order_by('-updated_at')
        return Response(ClaimSerializer(approved_claims, many=True).data)

