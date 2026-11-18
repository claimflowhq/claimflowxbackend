use soroban_sdk::{contracttype, Address, String};

#[contracttype]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum ClaimStatus {
    Submitted = 0,
    UnderReview = 1,
    Approved = 2,
    Rejected = 3,
    PayoutAuthorized = 4,
    Settled = 5,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClaimRecord {
    pub claim_id: String,
    pub claimant: Address,
    pub policy_id: String,
    pub requested_amount: i128,
    pub approved_amount: i128,
    pub authorized_payout_amount: i128,
    pub status: ClaimStatus,
    pub reviewer: Option<Address>,
    pub decision_notes: String,
    pub settlement_ref: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Reviewer(Address),
    Claim(String),
    ClaimsCount,
    ClaimIndex(u32),
}

