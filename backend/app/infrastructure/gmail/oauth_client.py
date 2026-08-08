from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.constants import (
    GOOGLE_AUTHORIZATION_ENDPOINT,
    GOOGLE_OAUTH_SCOPES,
    GOOGLE_TOKEN_ENDPOINT,
    GOOGLE_USERINFO_ENDPOINT,
)
from app.domain.exceptions.auth import OAuthExchangeError


@dataclass
class GoogleTokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str
    token_type: str


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    name: str
    email_verified: bool


class GoogleOAuthClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http_client

    def build_authorization_url(self, *, state: str) -> str:

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_OAUTH_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, *, code: str) -> GoogleTokenResponse:
        try:
            response = await self._http.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OAuthExchangeError(
                "Failed to exchange authorization code for tokens with Google."
            ) from exc

        body = response.json()
        return GoogleTokenResponse(
            access_token=body["access_token"],
            refresh_token=body.get(
                "refresh_token"
            ),  # absent on a repeat login without prompt=consent
            expires_in=body["expires_in"],
            scope=body.get("scope", ""),
            token_type=body.get("token_type", "Bearer"),
        )

    async def fetch_userinfo(self, *, access_token: str) -> GoogleUserInfo:
        """Fetch the authenticated user's identity from Google's userinfo endpoint."""
        try:
            response = await self._http.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OAuthExchangeError("Failed to fetch user info from Google.") from exc

        body = response.json()
        return GoogleUserInfo(
            sub=body["sub"],
            email=body["email"],
            name=body.get("name", body["email"]),
            email_verified=bool(body.get("email_verified", False)),
        )
