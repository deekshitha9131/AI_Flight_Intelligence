import sys
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_profile_security():
    print("--- STEP 1: LOGIN ---")
    login_resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "Password123!"}
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code} - {login_resp.text}")
        # Try registering if demo user doesn't exist
        reg_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "first_name": "Demo",
                "last_name": "User",
                "email": "demo@example.com",
                "password": "Password123!"
            }
        )
        print(f"Register status: {reg_resp.status_code}")
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )

    assert login_resp.status_code == 200, f"Failed login: {login_resp.text}"
    token = login_resp.json()["data"]["access_token"]
    print("Login successful! Token acquired.")

    print("\n--- STEP 2: GET /api/v1/auth/me ---")
    me_resp = requests.get(
        f"{BASE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200, f"Failed get profile: {me_resp.text}"
    data = me_resp.json()
    print("Profile API Response:")
    print(data)

    user_payload = data.get("data", {})
    
    # SECURITY ASSERTIONS
    assert "password" not in user_payload, "SECURITY VIOLATION: password field present in profile API response!"
    assert "password_hash" not in user_payload, "SECURITY VIOLATION: password_hash field present in profile API response!"
    assert "hashed_password" not in user_payload, "SECURITY VIOLATION: hashed_password present in profile API response!"
    assert "access_token" not in user_payload, "SECURITY VIOLATION: access_token in profile API response!"
    assert "refresh_token" not in user_payload, "SECURITY VIOLATION: refresh_token in profile API response!"

    print("\n✅ SECURITY VERIFICATION PASSED: No password, password_hash, or secret tokens found in profile response!")

if __name__ == "__main__":
    test_profile_security()
