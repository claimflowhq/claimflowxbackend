from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Policy
from .serializers import PolicySerializer
from apps.authentication.permissions import IsReviewerOrAdmin

@extend_schema_view(
    list=extend_schema(summary="List policies", description="Claimants view their own policies. Reviewers and admins view all policies."),
    retrieve=extend_schema(summary="Retrieve policy details"),
    create=extend_schema(summary="Create a new policy (Admins/Reviewers)"),
    update=extend_schema(summary="Update policy"),
    destroy=extend_schema(summary="Delete policy"),
)
class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    filterset_fields = ('category', 'is_active')
    search_fields = ('policy_number', 'policyholder__username', 'policyholder__email')
    ordering_fields = ('created_at', 'coverage_limit', 'start_date')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsReviewerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Policy.objects.none()
        if user.is_reviewer or user.is_admin_user:
            return Policy.objects.all()
        return Policy.objects.filter(policyholder=user)

    def perform_create(self, serializer):
        # If policyholder is not explicitly provided, default to requesting user
        if 'policyholder' not in serializer.validated_data:
            serializer.save(policyholder=self.request.user)
        else:
            serializer.save()

