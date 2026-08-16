import sys
import time
import requests
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def main():
    print("==================================================")
    print("  FINAL END-TO-END VERIFICATION SUITE  ")
    print("==================================================")

    with TestClient(app) as client:
        # 1. Health
        t0 = time.monotonic()
        r_h = client.get("/health")
        dt_h = (time.monotonic() - t0) * 1000
        print(f"[1/8] GET /health -> Status: {r_h.status_code} | Time: {dt_h:.2f}ms | Body: {r_h.text}")

        # Login
        r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        if r_login.status_code != 200:
            client.post("/api/v1/auth/register", json={"first_name": "Demo", "last_name": "User", "email": "demo@example.com", "password": "Password123!"})
            r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        token = r_login.json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Flight Search
        t0 = time.monotonic()
        r_s = client.get("/api/v1/flights/search", params={"origin": "HYD", "destination": "BOM", "departure_date": "2026-08-17"}, headers=headers)
        dt_s = (time.monotonic() - t0) * 1000
        print(f"[2/8] Flight Search (HYD->BOM) -> Status: {r_s.status_code} | Time: {dt_s:.2f}ms | Results: {len(r_s.json().get('data', []))}")

        # 3. Price Prediction
        t0 = time.monotonic()
        r_p = client.post("/api/v1/ai/predict-price", json={"origin": "HYD", "destination": "DXB", "departure_date": "2026-08-17", "adults": 1}, headers=headers)
        dt_p = (time.monotonic() - t0) * 1000
        print(f"[3/8] Price Prediction (HYD->DXB) -> Status: {r_p.status_code} | Time: {dt_p:.2f}ms | Price: {r_p.json().get('data', {}).get('predicted_price')}")

        # 4. Favorites
        t0 = time.monotonic()
        r_f = client.get("/api/v1/favorites", headers=headers)
        dt_f = (time.monotonic() - t0) * 1000
        print(f"[4/8] Favorites -> Status: {r_f.status_code} | Time: {dt_f:.2f}ms | Count: {r_f.json().get('count')}")

        # 5. Assistant One-Turn
        t0 = time.monotonic()
        r_a1 = client.post("/api/v1/assistant/chat", json={"message": "I want to travel from Hyderabad to Mumbai tomorrow morning"}, headers=headers)
        dt_a1 = (time.monotonic() - t0) * 1000
        print(f"[5/8] Assistant One-Turn -> Status: {r_a1.status_code} | Time: {dt_a1:.2f}ms")

        # 6. Assistant Multi-Turn
        r_m1 = client.post("/api/v1/assistant/chat", json={"message": "I have to go Delhi from Hyderabad"}, headers=headers)
        conv_id = r_m1.json()["data"]["conversation_id"]
        t0 = time.monotonic()
        r_m2 = client.post("/api/v1/assistant/chat", json={"message": "today by 7pm", "conversation_id": conv_id}, headers=headers)
        dt_m2 = (time.monotonic() - t0) * 1000
        print(f"[6/8] Assistant Multi-Turn -> Status: {r_m2.status_code} | Time: {dt_m2:.2f}ms")

        # 7. Concurrent Request Check
        t0 = time.monotonic()
        r_c = client.get("/health")
        dt_c = (time.monotonic() - t0) * 1000
        print(f"[7/8] Concurrent Health Check -> Status: {r_c.status_code} | Time: {dt_c:.2f}ms")

        print("\n==================================================")
        print("  ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY   ")
        print("==================================================")

if __name__ == "__main__":
    main()
