#![no_std]

mod errors;
mod types;

#[cfg(test)]
mod test;

use errors::ContractError;
use types::{ClaimRecord, ClaimStatus, DataKey};

use soroban_sdk::{contract, contractimpl, symbol_short, Address, Env, String};

#[contract]
pub struct ClaimFlowContract;

#[contractimpl]
impl ClaimFlowContract {
    /// Initialize the contract with an admin address.
    pub fn initialize(env: Env, admin: Address) -> Result<(), ContractError> {
        if env.storage().instance().has(&DataKey::Admin) {
            return Err(ContractError::AlreadyInitialized);
        }
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::ClaimsCount, &0u32);

        // Admin is also granted reviewer status by default
        env.storage().persistent().set(&DataKey::Reviewer(admin.clone()), &true);

        env.events().publish((symbol_short!("init"),), admin);
        Ok(())
    }

    /// Check if the caller is the contract admin.
    pub fn get_admin(env: Env) -> Result<Address, ContractError> {
        env.storage()
            .instance()
            .get(&DataKey::Admin)
            .ok_or(ContractError::NotInitialized)
    }

    /// Authorize a new reviewer (admin only).
    pub fn add_reviewer(env: Env, caller: Address, reviewer: Address) -> Result<(), ContractError> {
        caller.require_auth();
        let admin = Self::get_admin(env.clone())?;
        if caller != admin {
            return Err(ContractError::Unauthorized);
        }

        if env.storage().persistent().has(&DataKey::Reviewer(reviewer.clone())) {
            return Err(ContractError::ReviewerAlreadyExists);
        }

        env.storage().persistent().set(&DataKey::Reviewer(reviewer.clone()), &true);
        env.events().publish((symbol_short!("rev_add"),), reviewer);
        Ok(())
    }

    /// Remove a reviewer (admin only).
    pub fn remove_reviewer(env: Env, caller: Address, reviewer: Address) -> Result<(), ContractError> {
        caller.require_auth();
        let admin = Self::get_admin(env.clone())?;
        if caller != admin {
            return Err(ContractError::Unauthorized);
        }

        if !env.storage().persistent().has(&DataKey::Reviewer(reviewer.clone())) {
            return Err(ContractError::ReviewerNotFound);
        }

        env.storage().persistent().remove(&DataKey::Reviewer(reviewer.clone()));
        env.events().publish((symbol_short!("rev_rm"),), reviewer);
        Ok(())
    }

    /// Check if an address has reviewer rights.
    pub fn is_reviewer(env: Env, account: Address) -> bool {
        env.storage()
            .persistent()
            .get::<DataKey, bool>(&DataKey::Reviewer(account))
            .unwrap_or(false)
    }

    /// Register a new insurance claim.
    pub fn register_claim(
        env: Env,
        claimant: Address,
        claim_id: String,
        policy_id: String,
        requested_amount: i128,
    ) -> Result<(), ContractError> {
        claimant.require_auth();

        if requested_amount <= 0 || claim_id.len() == 0 || policy_id.len() == 0 {
            return Err(ContractError::InvalidInput);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        if env.storage().persistent().has(&claim_key) {
            return Err(ContractError::ClaimAlreadyExists);
        }

        let now = env.ledger().timestamp();
        let empty_notes = String::from_str(&env, "");
        let empty_settlement = String::from_str(&env, "");

        let claim = ClaimRecord {
            claim_id: claim_id.clone(),
            claimant: claimant.clone(),
            policy_id,
            requested_amount,
            approved_amount: 0,
            authorized_payout_amount: 0,
            status: ClaimStatus::Submitted,
            reviewer: None,
            decision_notes: empty_notes,
            settlement_ref: empty_settlement,
            created_at: now,
            updated_at: now,
        };

        env.storage().persistent().set(&claim_key, &claim);

        let mut count: u32 = env
            .storage()
            .instance()
            .get(&DataKey::ClaimsCount)
            .unwrap_or(0);
        env.storage().persistent().set(&DataKey::ClaimIndex(count), &claim_id);
        count += 1;
        env.storage().instance().set(&DataKey::ClaimsCount, &count);

        env.events().publish((symbol_short!("clm_reg"), claim_id), (claimant, requested_amount));
        Ok(())
    }

    /// Authorized reviewer moves claim to UnderReview.
    pub fn move_to_review(env: Env, reviewer: Address, claim_id: String) -> Result<(), ContractError> {
        reviewer.require_auth();
        if !Self::is_reviewer(env.clone(), reviewer.clone()) {
            return Err(ContractError::Unauthorized);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        let mut claim: ClaimRecord = env
            .storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)?;

        if claim.status != ClaimStatus::Submitted {
            return Err(ContractError::InvalidStateTransition);
        }

        claim.status = ClaimStatus::UnderReview;
        claim.reviewer = Some(reviewer.clone());
        claim.updated_at = env.ledger().timestamp();

        env.storage().persistent().set(&claim_key, &claim);
        env.events().publish((symbol_short!("clm_rev"), claim_id), reviewer);
        Ok(())
    }

    /// Authorized reviewer approves claim and sets approved amount.
    pub fn approve_claim(
        env: Env,
        reviewer: Address,
        claim_id: String,
        approved_amount: i128,
        decision_notes: String,
    ) -> Result<(), ContractError> {
        reviewer.require_auth();
        if !Self::is_reviewer(env.clone(), reviewer.clone()) {
            return Err(ContractError::Unauthorized);
        }

        if approved_amount <= 0 {
            return Err(ContractError::InvalidAmount);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        let mut claim: ClaimRecord = env
            .storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)?;

        if claim.status != ClaimStatus::UnderReview {
            return Err(ContractError::InvalidStateTransition);
        }

        claim.status = ClaimStatus::Approved;
        claim.approved_amount = approved_amount;
        claim.reviewer = Some(reviewer.clone());
        claim.decision_notes = decision_notes;
        claim.updated_at = env.ledger().timestamp();

        env.storage().persistent().set(&claim_key, &claim);
        env.events().publish((symbol_short!("clm_app"), claim_id), (reviewer, approved_amount));
        Ok(())
    }

    /// Authorized reviewer rejects claim.
    pub fn reject_claim(
        env: Env,
        reviewer: Address,
        claim_id: String,
        decision_notes: String,
    ) -> Result<(), ContractError> {
        reviewer.require_auth();
        if !Self::is_reviewer(env.clone(), reviewer.clone()) {
            return Err(ContractError::Unauthorized);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        let mut claim: ClaimRecord = env
            .storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)?;

        if claim.status != ClaimStatus::UnderReview {
            return Err(ContractError::InvalidStateTransition);
        }

        claim.status = ClaimStatus::Rejected;
        claim.reviewer = Some(reviewer.clone());
        claim.decision_notes = decision_notes;
        claim.updated_at = env.ledger().timestamp();

        env.storage().persistent().set(&claim_key, &claim);
        env.events().publish((symbol_short!("clm_rej"), claim_id), reviewer);
        Ok(())
    }

    /// Authorize payout for an approved claim (admin or reviewer).
    pub fn authorize_payout(
        env: Env,
        caller: Address,
        claim_id: String,
        payout_amount: i128,
    ) -> Result<(), ContractError> {
        caller.require_auth();
        if !Self::is_reviewer(env.clone(), caller.clone()) {
            return Err(ContractError::Unauthorized);
        }

        if payout_amount <= 0 {
            return Err(ContractError::InvalidAmount);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        let mut claim: ClaimRecord = env
            .storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)?;

        if claim.status == ClaimStatus::PayoutAuthorized || claim.status == ClaimStatus::Settled {
            return Err(ContractError::PayoutAlreadyAuthorized);
        }

        if claim.status != ClaimStatus::Approved {
            return Err(ContractError::InvalidStateTransition);
        }

        if payout_amount > claim.approved_amount {
            return Err(ContractError::PayoutExceedsApproved);
        }

        claim.status = ClaimStatus::PayoutAuthorized;
        claim.authorized_payout_amount = payout_amount;
        claim.updated_at = env.ledger().timestamp();

        env.storage().persistent().set(&claim_key, &claim);
        env.events().publish((symbol_short!("pay_auth"), claim_id), (caller, payout_amount));
        Ok(())
    }

    /// Mark an authorized claim as settled with an external settlement transaction reference.
    pub fn settle_claim(
        env: Env,
        caller: Address,
        claim_id: String,
        settlement_ref: String,
    ) -> Result<(), ContractError> {
        caller.require_auth();
        if !Self::is_reviewer(env.clone(), caller.clone()) {
            return Err(ContractError::Unauthorized);
        }

        let claim_key = DataKey::Claim(claim_id.clone());
        let mut claim: ClaimRecord = env
            .storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)?;

        if claim.status != ClaimStatus::PayoutAuthorized {
            return Err(ContractError::InvalidStateTransition);
        }

        claim.status = ClaimStatus::Settled;
        claim.settlement_ref = settlement_ref.clone();
        claim.updated_at = env.ledger().timestamp();

        env.storage().persistent().set(&claim_key, &claim);
        env.events().publish((symbol_short!("settled"), claim_id), settlement_ref);
        Ok(())
    }

    /// Read a claim record.
    pub fn get_claim(env: Env, claim_id: String) -> Result<ClaimRecord, ContractError> {
        let claim_key = DataKey::Claim(claim_id);
        env.storage()
            .persistent()
            .get(&claim_key)
            .ok_or(ContractError::ClaimNotFound)
    }

    /// Check if a claim exists.
    pub fn claim_exists(env: Env, claim_id: String) -> bool {
        let claim_key = DataKey::Claim(claim_id);
        env.storage().persistent().has(&claim_key)
    }

    /// Total registered claims.
    pub fn get_total_claims(env: Env) -> u32 {
        env.storage()
            .instance()
            .get(&DataKey::ClaimsCount)
            .unwrap_or(0)
    }

    /// Get claim ID by index.
    pub fn get_claim_by_index(env: Env, index: u32) -> Result<String, ContractError> {
        env.storage()
            .persistent()
            .get(&DataKey::ClaimIndex(index))
            .ok_or(ContractError::ClaimNotFound)
    }
}

