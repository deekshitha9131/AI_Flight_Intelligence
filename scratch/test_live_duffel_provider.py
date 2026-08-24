import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

from app.integrations.providers.duffel_provider import DuffelProvider
from app.schemas.flight import FlightSearchParams, TravelClass


async def main():
    token = os.getenv("DUFFEL_ACCESS_TOKEN") or os.getenv("DUFFEL_API_TOKEN")
    if not token:
        print("ERROR: No Duffel token found in environment.")
        return

    print("==================================================")
    print("      REAL DUFFEL API INTEGRATION VERIFICATION    ")
    print("==================================================")

    provider = DuffelProvider(api_token=token)
    dep_date = date.today() + timedelta(days=7)

    routes = [
        ("HYD", "BOM"),
        ("HYD", "DEL"),
        ("JFK", "LAX"),
    ]

    for orig, dest in routes:
        print(f"\n--- Testing Route: {orig} -> {dest} on {dep_date} ---")
        params = FlightSearchParams(
            origin=orig,
            destination=dest,
            departure_date=dep_date,
            adults=1,
            travel_class=TravelClass.ECONOMY,
            currency="USD",
            max_results=5,
        )

        try:
            raw_response = await provider.search_flights(params)
            offers = raw_response.get("data", [])
            carriers = raw_response.get("dictionaries", {}).get("carriers", {})

            print(f"HTTP Status: 201 Success")
            print(f"Number of offers returned: {len(offers)}")

            if offers:
                first = offers[0]
                first_seg = first["itineraries"][0]["segments"][0]
                carrier_code = first_seg["carrierCode"]
                airline_name = carriers.get(carrier_code, carrier_code)
                flight_num = first_seg["number"]
                price = first["price"]["grandTotal"]
                currency = first["price"]["currency"]

                print(f"Example Airline: {airline_name} ({carrier_code})")
                print(f"Flight Number: {flight_num}")
                print(f"Departure: {first_seg['departure']['at']}")
                print(f"Arrival: {first_seg['arrival']['at']}")
                print(f"Price: {price} {currency}")
            else:
                print("No offers returned for this route.")

        except Exception as exc:
            print(f"FAILED for route {orig} -> {dest}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
