import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.ai.llm_provider import GeminiProvider
from app.dependencies.ai import get_llm_provider

async def hanging_complete(*args, **kwargs):
    await asyncio.sleep(10.0)
    return "Hanging", 0

def main():
    print("=== PERFORMANCE & RECOVERY TEST ===")
    mock_gemini = GeminiProvider(api_key="test_key")
    app.dependency_overrides[get_llm_provider] = lambda: mock_gemini

    with TestClient(app) as client:
        # Login
        r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        if r_login.status_code != 200:
            client.post("/api/v1/auth/register", json={"first_name": "Demo", "last_name": "User", "email": "demo@example.com", "password": "Password123!"})
            r_login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        token = r_login.json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        print("\nTesting Assistant when Gemini is hanging (10s mock delay)...")
        t0 = time.monotonic()
        with patch.object(mock_gemini, "complete", side_effect=hanging_complete):
            r_ast = client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hyderabad to Mumbai tomorrow morning"},
                headers=headers,
            )
        elapsed = time.monotonic() - t0
        print(f"Assistant Status: {r_ast.status_code} | Time: {elapsed:.2f}s")
        print(f"Reply: {r_ast.json().get('data', {}).get('reply')[:120]}...")

        # Test other endpoints responsiveness
        t_h = time.monotonic()
        r_h = client.get("/health")
        print(f"Health Status: {r_h.status_code} | Time: {(time.monotonic() - t_h)*1000:.2f}ms")

        t_f = time.monotonic()
        r_f = client.get("/api/v1/flights/search", params={"origin": "HYD", "destination": "BOM", "departure_date": "2026-08-17"}, headers=headers)
        print(f"Flight Search Status: {r_f.status_code} | Time: {(time.monotonic() - t_f)*1000:.2f}ms")

        t_p = time.monotonic()
        r_p = client.post("/api/v1/ai/predict-price", json={"origin": "HYD", "destination": "DXB", "departure_date": "2026-08-17", "adults": 1}, headers=headers)
        print(f"Price Prediction Status: {r_p.status_code} | Time: {(time.monotonic() - t_p)*1000:.2f}ms")

if __name__ == "__main__":
    main()
