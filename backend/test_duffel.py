import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DUFFEL_ACCESS_TOKEN")

if not token:
    raise RuntimeError("DUFFEL_ACCESS_TOKEN is missing")

url = "https://api.duffel.com/air/offer_requests"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Duffel-Version": "v2",
}

payload = {
    "data": {
        "cabin_class": "economy",
        "slices": [
            {
                "origin": "JFK",
                "destination": "EWR",
                "departure_date": "2026-08-20",
            }
        ],
        "passengers": [
            {
                "type": "adult"
            }
        ],
    }
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=15,
)

print("HTTP STATUS:", response.status_code)
print(response.text)