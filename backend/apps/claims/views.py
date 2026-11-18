from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from .models import (
    Claim, ClaimStatus, SupportingEvidence,
    ClaimTimelineEvent, PayoutAuthorization
)
from .serializers import (
    ClaimSerializer,
    ClaimCreateSerializer,
    ClaimApproveActionSerializer,
    ClaimRejectActionSerializer,
    PayoutAuthorizeActionSerializer,
    ClaimSettleActionSerializer,
    SupportingEvidenceSerializer,
    ClaimTimelineEventSerializer,
    PayoutAuthorizationSerializer,
    DashboardMetricsSerializer,
)
from .services import ClaimService
from apps.authentication.permissions import IsReviewerOrAdmin

@extend_schema_view(
    list=extend_schema(summary="List insurance claims", description="Filter claims by status, category, policy, claimant."),
    retrieve=extend_schema(summary="Retrieve claim details"),
    create=extend_schema(summary="Submit a new insurance claim", description="Claimants create a claim with incident details, requested amount, and policy reference."),
)
class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Claim.objects.all().select_related('claimant', 'policy', 'assigned_reviewer').prefetch_related('evidence', 'timeline')
    serializer_class = ClaimSerializer
    filterset_fields = ('status', 'category', 'policy', 'claimant')
    search_fields = ('claim_reference', 'incident_description', 'policy__policy_number', 'claimant__username')
    ordering_fields = ('created_at', 'requested_amount', 'approved_amount', 'status')

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Claim.objects.none()
        if user.is_reviewer or user.is_admin_user:
            return Claim.objects.all()
        return Claim.objects.filter(claimant=user)

    def create(self, request, *args, **kwargs):
        serializer = ClaimCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        evidence_list = request.data.get('evidence', [])

        claim = ClaimService.create_claim(
            claimant=request.user,
            policy=data['policy'],
            category=data['category'],
            incident_description=data['incident_description'],
            incident_date=data['incident_date'],
            requested_amount=data['requested_amount'],
            evidence_list=evidence_list
        )

        return Response(
            ClaimSerializer(claim).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Move claim to Under Review",
        description="Authorized reviewer assigns the claim and transitions status to Under Review on-chain.",
        request=None,
        responses={200: ClaimSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsReviewerOrAdmin])
    def review(self, request, pk=None):
        claim = self.get_object()
        updated_claim = ClaimService.move_to_review(claim, request.user)
        return Response(ClaimSerializer(updated_claim).data)

    @extend_schema(
        summary="Approve claim",
        description="Authorized reviewer approves claim with an approved amount and decision notes, recording the approval on Soroban.",
        request=ClaimApproveActionSerializer,
        responses={200: ClaimSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsReviewerOrAdmin])
    def approve(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimApproveActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_claim = ClaimService.approve_claim(
            claim=claim,
            reviewer=request.user,
            approved_amount=serializer.validated_data['approved_amount'],
            notes=serializer.validated_data['notes']
        )
        return Response(ClaimSerializer(updated_claim).data)

    @extend_schema(
        summary="Reject claim",
        description="Authorized reviewer rejects claim with comments, recording the decision on Soroban.",
        request=ClaimRejectActionSerializer,
        responses={200: ClaimSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsReviewerOrAdmin])
    def reject(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimRejectActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_claim = ClaimService.reject_claim(
            claim=claim,
            reviewer=request.user,
            notes=serializer.validated_data['notes']
        )
        return Response(ClaimSerializer(updated_claim).data)

    @extend_schema(
        summary="Authorize payout on Soroban",
        description="Authorized reviewer or admin authorizes payout for an approved claim. Validates amount and prevents duplicate authorization.",
        request=PayoutAuthorizeActionSerializer,
        responses={200: PayoutAuthorizationSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsReviewerOrAdmin])
    def authorize_payout(self, request, pk=None):
        claim = self.get_object()
        serializer = PayoutAuthorizeActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payout = ClaimService.authorize_payout(
            claim=claim,
            user=request.user,
            payout_amount=serializer.validated_data['payout_amount']
        )
        return Response(PayoutAuthorizationSerializer(payout).data)

    @extend_schema(
        summary="Record actual settlement",
        description="Records confirmed Stellar Testnet transaction settlement. Clearly distinguishes authorization from fund settlement.",
        request=ClaimSettleActionSerializer,
        responses={200: ClaimSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsReviewerOrAdmin])
    def settle(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimSettleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_claim = ClaimService.settle_claim(
            claim=claim,
            user=request.user,
            settlement_reference=serializer.validated_data['settlement_reference']
        )
        return Response(ClaimSerializer(updated_claim).data)

    @extend_schema(
        summary="Claim activity history timeline",
        description="Chronological audit history of state changes, reviewers, notes, and transaction hashes.",
        responses={200: ClaimTimelineEventSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        claim = self.get_object()
        events = claim.timeline.all().order_by('timestamp')
        return Response(ClaimTimelineEventSerializer(events, many=True).data)

    @extend_schema(
        summary="Attach supporting evidence",
        description="Upload or link supporting evidence documents.",
        request=SupportingEvidenceSerializer,
        responses={201: SupportingEvidenceSerializer}
    )
    @action(detail=True, methods=['post'])
    def evidence(self, request, pk=None):
        claim = self.get_object()
        serializer = SupportingEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save(claim=claim)
        return Response(SupportingEvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

class DashboardMetricsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Dashboard operational metrics",
        description="Summary statistics across claims, states, requested vs authorized volumes.",
        responses={200: DashboardMetricsSerializer}
    )
    def get(self, request):
        user = request.user
        claims_qs = Claim.objects.all() if (user.is_reviewer or user.is_admin_user) else Claim.objects.filter(claimant=user)

        total_claims = claims_qs.count()
        submitted = claims_qs.filter(status=ClaimStatus.SUBMITTED).count()
        under_review = claims_qs.filter(status=ClaimStatus.UNDER_REVIEW).count()
        approved = claims_qs.filter(status=ClaimStatus.APPROVED).count()
        rejected = claims_qs.filter(status=ClaimStatus.REJECTED).count()
        payout_auth = claims_qs.filter(status=ClaimStatus.PAYOUT_AUTHORIZED).count()
        settled = claims_qs.filter(status=ClaimStatus.SETTLED).count()

        total_req = claims_qs.aggregate(Sum('requested_amount'))['requested_amount__sum'] or Decimal('0.00')
        total_auth = claims_qs.filter(authorized_payout_amount__isnull=False).aggregate(Sum('authorized_payout_amount'))['authorized_payout_amount__sum'] or Decimal('0.00')
        total_settled = claims_qs.filter(status=ClaimStatus.SETTLED, authorized_payout_amount__isnull=False).aggregate(Sum('authorized_payout_amount'))['authorized_payout_amount__sum'] or Decimal('0.00')

        data = {
            'total_claims': total_claims,
            'submitted_claims': submitted,
            'under_review_claims': under_review,
            'approved_claims': approved,
            'rejected_claims': rejected,
            'payout_authorized_claims': payout_auth,
            'settled_claims': settled,
            'total_requested_volume': total_req,
            'total_authorized_payout_volume': total_auth,
            'total_settled_volume': total_settled,
        }
        return Response(DashboardMetricsSerializer(data).data)

