use super::*;
use crate::errors::ContractError;
use crate::types::ClaimStatus;
use soroban_sdk::{testutils::Address as _, Address, Env, String};

struct TestFixture {
    env: Env,
    admin: Address,
    reviewer: Address,
    unauthorized: Address,
    claimant: Address,
    client: ClaimFlowContractClient<'static>,
}

fn setup_test() -> TestFixture {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register(ClaimFlowContract, ());
    let client = ClaimFlowContractClient::new(&env, &contract_id);

    let admin = Address::generate(&env);
    let reviewer = Address::generate(&env);
    let unauthorized = Address::generate(&env);
    let claimant = Address::generate(&env);

    client.initialize(&admin);
    client.add_reviewer(&admin, &reviewer);

    TestFixture {
        env,
        admin,
        reviewer,
        unauthorized,
        claimant,
        client,
    }
}

#[test]
fn test_scenario_01_submit_valid_claim() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-20261116-0001");
    let policy_id = String::from_str(&f.env, "POL-HEALTH-991");
    let amount: i128 = 500_0000000; // 500 USDC

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &amount);

    assert!(f.client.claim_exists(&claim_id));
    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.claim_id, claim_id);
    assert_eq!(claim.claimant, f.claimant);
    assert_eq!(claim.policy_id, policy_id);
    assert_eq!(claim.requested_amount, amount);
    assert_eq!(claim.approved_amount, 0);
    assert_eq!(claim.authorized_payout_amount, 0);
    assert_eq!(claim.status, ClaimStatus::Submitted);
    assert_eq!(f.client.get_total_claims(), 1);
}

#[test]
fn test_scenario_02_submit_incomplete_claim_validation_error() {
    let f = setup_test();
    let valid_claim_id = String::from_str(&f.env, "CLM-0002");
    let valid_policy = String::from_str(&f.env, "POL-1");

    // Zero or negative amount should fail
    let res_zero = f.client.try_register_claim(&f.claimant, &valid_claim_id, &valid_policy, &0);
    assert_eq!(res_zero, Err(Ok(ContractError::InvalidInput)));

    let res_neg = f.client.try_register_claim(&f.claimant, &valid_claim_id, &valid_policy, &-100);
    assert_eq!(res_neg, Err(Ok(ContractError::InvalidInput)));

    // Empty claim_id should fail
    let empty_id = String::from_str(&f.env, "");
    let res_empty_id = f.client.try_register_claim(&f.claimant, &empty_id, &valid_policy, &1000);
    assert_eq!(res_empty_id, Err(Ok(ContractError::InvalidInput)));

    // Empty policy_id should fail
    let empty_policy = String::from_str(&f.env, "");
    let res_empty_pol = f.client.try_register_claim(&f.claimant, &valid_claim_id, &empty_policy, &1000);
    assert_eq!(res_empty_pol, Err(Ok(ContractError::InvalidInput)));
}

#[test]
fn test_scenario_03_generate_unique_claim_reference() {
    let f = setup_test();
    let claim_id1 = String::from_str(&f.env, "CLM-20261116-0003A");
    let claim_id2 = String::from_str(&f.env, "CLM-20261116-0003B");
    let policy_id = String::from_str(&f.env, "POL-AUTO-100");

    f.client.register_claim(&f.claimant, &claim_id1, &policy_id, &300);
    f.client.register_claim(&f.claimant, &claim_id2, &policy_id, &400);

    assert_eq!(f.client.get_total_claims(), 2);
    assert_eq!(f.client.get_claim_by_index(&0), claim_id1);
    assert_eq!(f.client.get_claim_by_index(&1), claim_id2);

    // Duplicate registration must fail
    let dup_res = f.client.try_register_claim(&f.claimant, &claim_id1, &policy_id, &500);
    assert_eq!(dup_res, Err(Ok(ContractError::ClaimAlreadyExists)));
}

#[test]
fn test_scenario_04_move_claim_to_review() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0004");
    let policy_id = String::from_str(&f.env, "POL-1");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);

    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::UnderReview);
    assert_eq!(claim.reviewer, Some(f.reviewer));
}

#[test]
fn test_scenario_05_authorized_reviewer_approves_claim() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0005");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Claim validated with incident report.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &400, &notes);

    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::Approved);
    assert_eq!(claim.approved_amount, 400);
    assert_eq!(claim.decision_notes, notes);
}

#[test]
fn test_scenario_06_authorized_reviewer_rejects_claim() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0006");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Policy does not cover reported incident type.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.reject_claim(&f.reviewer, &claim_id, &notes);

    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::Rejected);
    assert_eq!(claim.approved_amount, 0);
    assert_eq!(claim.decision_notes, notes);
}

#[test]
fn test_scenario_07_unauthorized_reviewer_attempts_approval() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0007");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Unauthorized attempt.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);

    // Unauthorized party attempts approval
    let res = f.client.try_approve_claim(&f.unauthorized, &claim_id, &400, &notes);
    assert_eq!(res, Err(Ok(ContractError::Unauthorized)));

    // Claim state remains unchanged
    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::UnderReview);
}

#[test]
fn test_scenario_08_approve_already_rejected_claim_fails() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0008");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Rejection notes.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.reject_claim(&f.reviewer, &claim_id, &notes);

    // Attempting to approve after rejection must be rejected
    let res = f.client.try_approve_claim(&f.reviewer, &claim_id, &400, &notes);
    assert_eq!(res, Err(Ok(ContractError::InvalidStateTransition)));
}

#[test]
fn test_scenario_09_authorize_payout_for_approved_claim() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0009");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Valid claim.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &450, &notes);

    // Admin or Reviewer authorizes payout up to approved amount
    f.client.authorize_payout(&f.reviewer, &claim_id, &450);

    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::PayoutAuthorized);
    assert_eq!(claim.authorized_payout_amount, 450);
}

#[test]
fn test_scenario_10_authorize_payout_for_rejected_claim_fails() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0010");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Rejected.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.reject_claim(&f.reviewer, &claim_id, &notes);

    // Payout authorization for rejected claim must fail
    let res = f.client.try_authorize_payout(&f.reviewer, &claim_id, &300);
    assert_eq!(res, Err(Ok(ContractError::InvalidStateTransition)));
}

#[test]
fn test_scenario_11_duplicate_payout_authorization_fails() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0011");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Approved.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &400, &notes);
    f.client.authorize_payout(&f.reviewer, &claim_id, &400);

    // Second authorization attempt must be rejected
    let res = f.client.try_authorize_payout(&f.reviewer, &claim_id, &400);
    assert_eq!(res, Err(Ok(ContractError::PayoutAlreadyAuthorized)));
}

#[test]
fn test_scenario_12_authorization_exceeds_approved_amount_fails() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0012");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Approved.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &300, &notes);

    // Attempting to authorize 350 when approved was only 300
    let res = f.client.try_authorize_payout(&f.reviewer, &claim_id, &350);
    assert_eq!(res, Err(Ok(ContractError::PayoutExceedsApproved)));
}

#[test]
fn test_scenario_13_unauthorized_claim_state_change() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0013");
    let policy_id = String::from_str(&f.env, "POL-1");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);

    // Unauthorized user attempts move_to_review
    let res_review = f.client.try_move_to_review(&f.unauthorized, &claim_id);
    assert_eq!(res_review, Err(Ok(ContractError::Unauthorized)));

    // Unauthorized user attempts payout authorization directly
    let res_payout = f.client.try_authorize_payout(&f.unauthorized, &claim_id, &500);
    assert_eq!(res_payout, Err(Ok(ContractError::Unauthorized)));
}

#[test]
fn test_scenario_14_failed_contract_transaction_state_remains_consistent() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0014");
    let policy_id = String::from_str(&f.env, "POL-1");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);

    // Attempt invalid direct payout authorization from Submitted state
    let _ = f.client.try_authorize_payout(&f.reviewer, &claim_id, &500);

    // Ensure state remained Submitted and unmodified
    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.status, ClaimStatus::Submitted);
    assert_eq!(claim.authorized_payout_amount, 0);
    assert_eq!(claim.approved_amount, 0);
}

#[test]
fn test_scenario_15_verify_authorization_history() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0015");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Thoroughly verified documents.");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &1000);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &800, &notes);
    f.client.authorize_payout(&f.reviewer, &claim_id, &800);

    let claim = f.client.get_claim(&claim_id);
    assert_eq!(claim.claim_id, claim_id);
    assert_eq!(claim.claimant, f.claimant);
    assert_eq!(claim.reviewer, Some(f.reviewer));
    assert_eq!(claim.requested_amount, 1000);
    assert_eq!(claim.approved_amount, 800);
    assert_eq!(claim.authorized_payout_amount, 800);
    assert_eq!(claim.status, ClaimStatus::PayoutAuthorized);
    assert_eq!(claim.decision_notes, notes);
}

#[test]
fn test_scenario_16_monitor_optional_actual_payment_settlement_tracked_separately() {
    let f = setup_test();
    let claim_id = String::from_str(&f.env, "CLM-0016");
    let policy_id = String::from_str(&f.env, "POL-1");
    let notes = String::from_str(&f.env, "Approved for settlement.");
    let settlement_tx = String::from_str(&f.env, "tx_stellar_testnet_a8f93d489b0123");

    f.client.register_claim(&f.claimant, &claim_id, &policy_id, &500);
    f.client.move_to_review(&f.reviewer, &claim_id);
    f.client.approve_claim(&f.reviewer, &claim_id, &500, &notes);
    f.client.authorize_payout(&f.reviewer, &claim_id, &500);

    // Pre-settlement state is PayoutAuthorized, NOT settled
    let claim_before = f.client.get_claim(&claim_id);
    assert_eq!(claim_before.status, ClaimStatus::PayoutAuthorized);

    // Authorized admin records settlement with the confirmed testnet tx hash
    f.client.settle_claim(&f.admin, &claim_id, &settlement_tx);

    let claim_after = f.client.get_claim(&claim_id);
    assert_eq!(claim_after.status, ClaimStatus::Settled);
    assert_eq!(claim_after.settlement_ref, settlement_tx);
}

