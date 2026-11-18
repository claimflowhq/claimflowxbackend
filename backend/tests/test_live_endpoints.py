"""
ClaimFlow End-to-End Live API Endpoint Integration Test Suite
Validates all endpoints against the running server.
"""
import uuid
import requests

def test_all_endpoints(base_url="http://localhost:8000"):
    api = f"{base_url}/api/v1"

    # Documentation
    r_schema = requests.get(f"{base_url}/api/schema/")
    assert r_schema.status_code == 200

    r_swagger = requests.get(f"{base_url}/api/docs/")
    assert r_swagger.status_code == 200

    r_redoc = requests.get(f"{base_url}/api/redoc/")
    assert r_redoc.status_code == 200
    assert "https://cdn.jsdelivr.net/npm/redoc@2.1.5" in r_redoc.text

    # User registration & auth
    u_claimant = f"claimant_{str(uuid.uuid4())[:8]}"
    r_reg_c = requests.post(f"{api}/auth/register/", json={
        "username": u_claimant,
        "email": f"{u_claimant}@claimflowx.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "role": "CLAIMANT",
        "wallet_address": "GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C"
    })
    assert r_reg_c.status_code == 201
    claimant_id = r_reg_c.json()['id']

    r_login_c = requests.post(f"{api}/auth/login/", json={
        "username": u_claimant,
        "password": "Password123!"
    })
    assert r_login_c.status_code == 200
    c_token = r_login_c.json()['access']
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # Reviewer
    u_reviewer = f"reviewer_{str(uuid.uuid4())[:8]}"
    r_reg_r = requests.post(f"{api}/auth/register/", json={
        "username": u_reviewer,
        "email": f"{u_reviewer}@claimflowx.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "role": "REVIEWER",
        "wallet_address": "GCREVIEWER000000000000000000000000000000000000000000000000"
    })
    assert r_reg_r.status_code == 201

    r_login_r = requests.post(f"{api}/auth/login/", json={
        "username": u_reviewer,
        "password": "Password123!"
    })
    assert r_login_r.status_code == 200
    r_token = r_login_r.json()['access']
    r_headers = {"Authorization": f"Bearer {r_token}"}

    # Policy
    r_pol = requests.post(f"{api}/policies/", json={
        "policy_number": f"POL-TEST-{uuid.uuid4().hex[:6].upper()}",
        "policyholder": claimant_id,
        "category": "AUTO",
        "coverage_limit": "7500.00",
        "deductible": "150.00",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "is_active": True
    }, headers=r_headers)
    assert r_pol.status_code == 201
    policy_id = r_pol.json()['id']

    # Submit claim
    r_clm = requests.post(f"{api}/claims/", json={
        "policy": policy_id,
        "category": "AUTO",
        "incident_description": "Windshield and side mirror repair.",
        "incident_date": "2026-11-15",
        "requested_amount": "500.00"
    }, headers=c_headers)
    assert r_clm.status_code == 201
    claim_id = r_clm.json()['id']
    claim_ref = r_clm.json()['claim_reference']

    # Evidence
    r_ev = requests.post(f"{api}/claims/{claim_id}/evidence/", json={
        "file_name": "windshield.jpg",
        "file_url": "https://storage.claimflowx.com/windshield.jpg",
        "document_type": "PHOTO"
    }, headers=c_headers)
    assert r_ev.status_code == 201

    # Reviewer workflow
    r_rev = requests.post(f"{api}/claims/{claim_id}/review/", headers=r_headers)
    assert r_rev.status_code == 200 and r_rev.json()['status'] == "UNDER_REVIEW"

    r_app = requests.post(f"{api}/claims/{claim_id}/approve/", json={
        "approved_amount": "480.00",
        "notes": "Cost estimate verified."
    }, headers=r_headers)
    assert r_app.status_code == 200 and r_app.json()['status'] == "APPROVED"

    r_auth = requests.post(f"{api}/claims/{claim_id}/authorize_payout/", json={
        "payout_amount": "480.00"
    }, headers=r_headers)
    assert r_auth.status_code == 200 and r_auth.json()['status'] == "CONFIRMED"

    r_settle = requests.post(f"{api}/claims/{claim_id}/settle/", json={
        "settlement_reference": "tx_stellar_testnet_settle_verified"
    }, headers=r_headers)
    assert r_settle.status_code == 200 and r_settle.json()['status'] == "SETTLED"

    # Dashboard & Blockchain
    r_timeline = requests.get(f"{api}/claims/{claim_id}/timeline/", headers=r_headers)
    assert r_timeline.status_code == 200

    r_payouts = requests.get(f"{api}/payouts/", headers=r_headers)
    assert r_payouts.status_code == 200

    r_txs = requests.get(f"{api}/blockchain/transactions/", headers=r_headers)
    assert r_txs.status_code == 200

    r_contract = requests.get(f"{api}/blockchain/contract-info/")
    assert r_contract.status_code == 200

    r_onchain = requests.get(f"{api}/blockchain/claims/{claim_ref}/", headers=r_headers)
    assert r_onchain.status_code == 200

    r_metrics = requests.get(f"{api}/claims/dashboard/metrics/", headers=r_headers)
    assert r_metrics.status_code == 200

    return True

if __name__ == '__main__':
    test_all_endpoints()
    print("All live endpoint tests passed!")

