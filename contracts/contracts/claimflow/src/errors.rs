use soroban_sdk::contracterror;

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum ContractError {
    AlreadyInitialized = 1,
    NotInitialized = 2,
    Unauthorized = 3,
    ClaimAlreadyExists = 4,
    ClaimNotFound = 5,
    InvalidStateTransition = 6,
    InvalidAmount = 7,
    PayoutExceedsApproved = 8,
    PayoutAlreadyAuthorized = 9,
    ReviewerAlreadyExists = 10,
    ReviewerNotFound = 11,
    InvalidInput = 12,
}

