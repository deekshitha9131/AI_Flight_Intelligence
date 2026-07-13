from __future__ import annotations

from fastapi import Request

from app.integrations.amadeus.client import AmadeusClient


def get_amadeus_client(request: Request) -> AmadeusClient:
    """Return the shared AmadeusClient stored on application state.

    Usage in an endpoint::

        @router.get("/example")
        async def example(client: AmadeusClient = Depends(get_amadeus_client)):
            data = await client.request("GET", "/v1/reference-data/locations", ...)
    """
    return request.app.state.amadeus
