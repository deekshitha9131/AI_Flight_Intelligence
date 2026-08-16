import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def main():
    print("Testing FastAPI app directly with TestClient...")
    with TestClient(app) as client:
        # 1. Health
        r_health = client.get("/health")
        print(f"GET /health status: {r_health.status_code} | body: {r_health.text}")

        # 2. Root
        r_root = client.get("/")
        print(f"GET / status: {r_root.status_code} | body: {r_root.text}")

        # 3. Login
        r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        if r_login.status_code != 200:
            client.post("/api/v1/auth/register", json={"first_name": "Demo", "last_name": "User", "email": "demo@example.com", "password": "Password123!"})
            r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})

        print(f"POST /api/v1/auth/login status: {r_login.status_code}")
        token = r_login.json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # 4. Flight Search
        r_flight = client.get("/api/v1/flights/search", params={"origin": "HYD", "destination": "BOM", "departure_date": "2026-08-17"}, headers=headers)
        print(f"GET /api/v1/flights/search status: {r_flight.status_code} | count: {len(r_flight.json().get('data', []))}")

        # 5. Price Prediction
        r_pred = client.post("/api/v1/ai/predict-price", json={"origin": "HYD", "destination": "DXB", "departure_date": "2026-08-17", "adults": 1}, headers=headers)
        print(f"POST /api/v1/ai/predict-price status: {r_pred.status_code} | price: {r_pred.json().get('data', {}).get('predicted_price')}")

        # 6. Favorites
        r_fav = client.get("/api/v1/favorites", headers=headers)
        print(f"GET /api/v1/favorites status: {r_fav.status_code} | count: {r_fav.json().get('count')}")

        # 7. Assistant
        r_ast = client.post("/api/v1/assistant/chat", json={"message": "I need a flight from Hyderabad to Mumbai tomorrow morning"}, headers=headers)
        print(f"POST /api/v1/assistant/chat status: {r_ast.status_code} | reply: {r_ast.json().get('data', {}).get('reply')[:100]}...")

if __name__ == "__main__":
    main()
