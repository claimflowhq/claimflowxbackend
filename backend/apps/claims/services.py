from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import (
    Claim, ClaimStatus, ClaimReviewDecision,
    PayoutAuthorization, ClaimTimelineEvent, SupportingEvidence
)
from apps.blockchain.soroban_client import soroban_service

class ClaimService:
    @staticmethod
    @transaction.atomic
    def create_claim(claimant, policy, category, incident_description, incident_date, requested_amount, evidence_list=None):
        if requested_amount <= Decimal('0.00'):
            raise ValidationError({"requested_amount": "Requested amount must be greater than 0."})

        if not policy.is_active:
            raise ValidationError({"policy": "Selected policy is not active."})

        if requested_amount > policy.coverage_limit:
            raise ValidationError({
                "requested_amount": f"Requested amount ({requested_amount}) exceeds policy coverage limit ({policy.coverage_limit})."
            })

        claim = Claim.objects.create(
            claimant=claimant,
            policy=policy,
            category=category,
            incident_description=incident_description,
            incident_date=incident_date,
            requested_amount=requested_amount,
            status=ClaimStatus.SUBMITTED
        )

        # Supporting evidence attachments if provided
        if evidence_list:
            for item in evidence_list:
                SupportingEvidence.objects.create(
                    claim=claim,
                    file_name=item.get('file_name', 'document.pdf'),
                    file_url=item.get('file_url', ''),
                    document_type=item.get('document_type', 'SUPPORTING_DOCUMENT'),
                    file_size_bytes=item.get('file_size_bytes', 0)
                )

        # Register on Soroban
        try:
            tx_record = soroban_service.register_claim(
                claim_id=claim.claim_reference,
                claimant_address=claimant.wallet_address or "",
                policy_id=policy.policy_number,
                requested_amount=requested_amount
            )
            claim.on_chain_tx_hash = tx_record.tx_hash
            claim.save(update_fields=['on_chain_tx_hash'])
            tx_hash = tx_record.tx_hash
        except Exception as e:
            tx_hash = None

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=claimant,
            action="CLAIM_SUBMITTED",
            from_status=ClaimStatus.DRAFT,
            to_status=ClaimStatus.SUBMITTED,
            details=f"Claim submitted by {claimant.username} for requested amount {requested_amount} USDC.",
            tx_hash=tx_hash
        )

        return claim

    @staticmethod
    @transaction.atomic
    def move_to_review(claim: Claim, reviewer):
        if not (reviewer.is_reviewer or reviewer.is_admin_user):
            raise PermissionDenied("Only authorized reviewers or administrators can move claims to review.")

        if claim.status != ClaimStatus.SUBMITTED:
            raise ValidationError(f"Cannot move claim from status '{claim.status}' to Under Review. Current status must be Submitted.")

        from_status = claim.status
        claim.status = ClaimStatus.UNDER_REVIEW
        claim.assigned_reviewer = reviewer
        claim.save(update_fields=['status', 'assigned_reviewer', 'updated_at'])

        try:
            tx_record = soroban_service.move_to_review(
                claim_id=claim.claim_reference,
                reviewer_address=reviewer.wallet_address or ""
            )
            tx_hash = tx_record.tx_hash
        except Exception:
            tx_hash = None

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=reviewer,
            action="MOVED_TO_REVIEW",
            from_status=from_status,
            to_status=ClaimStatus.UNDER_REVIEW,
            details=f"Claim assigned to reviewer {reviewer.username} for assessment.",
            tx_hash=tx_hash
        )

        return claim

    @staticmethod
    @transaction.atomic
    def approve_claim(claim: Claim, reviewer, approved_amount: Decimal, notes: str):
        if not (reviewer.is_reviewer or reviewer.is_admin_user):
            raise PermissionDenied("Only authorized reviewers can approve insurance claims.")

        if claim.status != ClaimStatus.UNDER_REVIEW:
            raise ValidationError(f"Cannot approve claim with status '{claim.status}'. Must be Under Review.")

        if approved_amount <= Decimal('0.00'):
            raise ValidationError({"approved_amount": "Approved amount must be positive."})

        if approved_amount > claim.policy.coverage_limit:
            raise ValidationError({
                "approved_amount": f"Approved amount ({approved_amount}) cannot exceed policy coverage limit ({claim.policy.coverage_limit})."
            })

        from_status = claim.status
        claim.status = ClaimStatus.APPROVED
        claim.approved_amount = approved_amount
        claim.assigned_reviewer = reviewer
        claim.save(update_fields=['status', 'approved_amount', 'assigned_reviewer', 'updated_at'])

        # Register on-chain
        try:
            tx_record = soroban_service.approve_claim(
                claim_id=claim.claim_reference,
                reviewer_address=reviewer.wallet_address or "",
                approved_amount=approved_amount,
                notes=notes
            )
            tx_hash = tx_record.tx_hash
        except Exception:
            tx_hash = None

        ClaimReviewDecision.objects.create(
            claim=claim,
            reviewer=reviewer,
            decision='APPROVED',
            approved_amount=approved_amount,
            notes=notes,
            tx_hash=tx_hash
        )

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=reviewer,
            action="CLAIM_APPROVED",
            from_status=from_status,
            to_status=ClaimStatus.APPROVED,
            details=f"Reviewer {reviewer.username} approved claim for {approved_amount} USDC. Notes: {notes}",
            tx_hash=tx_hash
        )

        return claim

    @staticmethod
    @transaction.atomic
    def reject_claim(claim: Claim, reviewer, notes: str):
        if not (reviewer.is_reviewer or reviewer.is_admin_user):
            raise PermissionDenied("Only authorized reviewers can reject insurance claims.")

        if claim.status != ClaimStatus.UNDER_REVIEW:
            raise ValidationError(f"Cannot reject claim with status '{claim.status}'. Must be Under Review.")

        from_status = claim.status
        claim.status = ClaimStatus.REJECTED
        claim.approved_amount = Decimal('0.00')
        claim.assigned_reviewer = reviewer
        claim.save(update_fields=['status', 'approved_amount', 'assigned_reviewer', 'updated_at'])

        try:
            tx_record = soroban_service.reject_claim(
                claim_id=claim.claim_reference,
                reviewer_address=reviewer.wallet_address or "",
                notes=notes
            )
            tx_hash = tx_record.tx_hash
        except Exception:
            tx_hash = None

        ClaimReviewDecision.objects.create(
            claim=claim,
            reviewer=reviewer,
            decision='REJECTED',
            approved_amount=Decimal('0.00'),
            notes=notes,
            tx_hash=tx_hash
        )

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=reviewer,
            action="CLAIM_REJECTED",
            from_status=from_status,
            to_status=ClaimStatus.REJECTED,
            details=f"Reviewer {reviewer.username} rejected claim. Reason: {notes}",
            tx_hash=tx_hash
        )

        return claim

    @staticmethod
    @transaction.atomic
    def authorize_payout(claim: Claim, user, payout_amount: Decimal):
        if not (user.is_reviewer or user.is_admin_user):
            raise PermissionDenied("Only authorized reviewers or administrators can authorize payouts.")

        if hasattr(claim, 'payout_authorization') or claim.status in (ClaimStatus.PAYOUT_AUTHORIZED, ClaimStatus.SETTLED):
            raise ValidationError("Payout has already been authorized for this claim (duplicate authorization prevented).")

        if claim.status != ClaimStatus.APPROVED:
            raise ValidationError(f"Cannot authorize payout for claim in '{claim.status}' state. Only Approved claims are eligible.")

        if payout_amount <= Decimal('0.00'):
            raise ValidationError({"payout_amount": "Payout amount must be greater than zero."})

        if payout_amount > claim.approved_amount:
            raise ValidationError({
                "payout_amount": f"Payout authorization amount ({payout_amount}) exceeds approved claim amount ({claim.approved_amount})."
            })

        from_status = claim.status
        claim.status = ClaimStatus.PAYOUT_AUTHORIZED
        claim.authorized_payout_amount = payout_amount
        claim.save(update_fields=['status', 'authorized_payout_amount', 'updated_at'])

        try:
            tx_record = soroban_service.authorize_payout(
                claim_id=claim.claim_reference,
                caller_address=user.wallet_address or "",
                payout_amount=payout_amount
            )
            tx_hash = tx_record.tx_hash
        except Exception:
            tx_hash = None

        payout = PayoutAuthorization.objects.create(
            claim=claim,
            authorized_by=user,
            amount=payout_amount,
            status='CONFIRMED',
            tx_hash=tx_hash
        )

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=user,
            action="PAYOUT_AUTHORIZED",
            from_status=from_status,
            to_status=ClaimStatus.PAYOUT_AUTHORIZED,
            details=f"Payout of {payout_amount} USDC authorized on Soroban smart contract by {user.username}.",
            tx_hash=tx_hash
        )

        return payout

    @staticmethod
    @transaction.atomic
    def settle_claim(claim: Claim, user, settlement_reference: str):
        if not (user.is_reviewer or user.is_admin_user):
            raise PermissionDenied("Only authorized administrators or reviewers can record payout settlement.")

        if claim.status != ClaimStatus.PAYOUT_AUTHORIZED:
            raise ValidationError(f"Cannot settle claim in status '{claim.status}'. Payout must be authorized first.")

        if not settlement_reference or not settlement_reference.strip():
            raise ValidationError({"settlement_reference": "A valid Stellar transaction hash or settlement reference is required."})

        from_status = claim.status
        claim.status = ClaimStatus.SETTLED
        claim.save(update_fields=['status', 'updated_at'])

        payout = claim.payout_authorization
        payout.settlement_reference = settlement_reference
        payout.settled_at = timezone.now()
        payout.save(update_fields=['settlement_reference', 'settled_at', 'updated_at'])

        try:
            tx_record = soroban_service.settle_claim(
                claim_id=claim.claim_reference,
                caller_address=user.wallet_address or "",
                settlement_ref=settlement_reference
            )
            tx_hash = tx_record.tx_hash
        except Exception:
            tx_hash = None

        ClaimTimelineEvent.objects.create(
            claim=claim,
            actor=user,
            action="CLAIM_SETTLED",
            from_status=from_status,
            to_status=ClaimStatus.SETTLED,
            details=f"Settlement confirmed via Stellar Testnet transaction {settlement_reference}.",
            tx_hash=tx_hash
        )

        return claim

