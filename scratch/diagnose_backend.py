import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, path, json_data=None, params=None, headers=None):
    url = f"{BASE_URL}{path}"
    print(f"\n--- Testing {name}: {method} {url} ---")
    t0 = time.monotonic()
    try:
        if method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=5)
        else:
            resp = requests.post(url, json=json_data, headers=headers, timeout=5)
        elapsed = (time.monotonic() - t0) * 1000
        print(f"Status: {resp.status_code} | Time: {elapsed:.2f}ms")
        print(f"Response: {resp.text[:300]}")
        return resp
    except Exception as exc:
        elapsed = (time.monotonic() - t0) * 1000
        print(f"FAILED / TIMED OUT after {elapsed:.2f}ms: {exc}")
        return None

def main():
    print("=== BACKEND DIAGNOSTIC TEST ===")
    health_resp = test_endpoint("Health", "GET", "/health")
    if not health_resp:
        # Also try /api/v1/health or root
        test_endpoint("Root /", "GET", "/")
        test_endpoint("API Health", "GET", "/api/v1/health")
        return

    # Login to get token
    login_resp = test_endpoint("Login", "POST", "/api/v1/auth/login", json_data={"email": "demo@example.com", "password": "Password123!"})
    token = None
    if login_resp and login_resp.status_code == 200:
        token = login_resp.json().get("data", {}).get("access_token")

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Test Flight Search
    test_endpoint("Flight Search", "GET", "/api/v1/flights/search", params={"origin": "HYD", "destination": "BOM", "departure_date": "2026-08-17"}, headers=headers)

    # Test Price Prediction
    test_endpoint("Price Prediction", "POST", "/api/v1/ai/predict-price", json_data={"origin": "HYD", "destination": "DXB", "departure_date": "2026-08-17", "adults": 1}, headers=headers)

    # Test Favorites
    test_endpoint("Favorites List", "GET", "/api/v1/favorites", headers=headers)

    # Test Assistant
    test_endpoint("Assistant Chat", "POST", "/api/v1/assistant/chat", json_data={"message": "hi"}, headers=headers)

if __name__ == "__main__":
    main()
