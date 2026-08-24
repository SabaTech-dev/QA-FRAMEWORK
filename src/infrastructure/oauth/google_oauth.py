"""Google OAuth Provider Implementation."""

from typing import Dict

import httpx

from domain.auth.entities import OAuthUser, Token

from .base_oauth import BaseOAuthProvider, OAuthUserInfoError


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth 2.0 provider implementation."""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google"

    @property
    def _authorization_url(self) -> str:
        return self.GOOGLE_AUTH_URL

    @property
    def _token_url(self) -> str:
        return self.GOOGLE_TOKEN_URL

    def _get_authorization_params(self, state: str, redirect_uri: str) -> Dict[str, str]:
        """Build Google OAuth authorization parameters."""
        return {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

    async def _exchange_code_impl(
        self,
        code: str,
        redirect_uri: str,
    ) -> httpx.Response:
        """Exchange authorization code for Google token."""
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        headers = {"Accept": "application/json"}
        return await self._make_request("POST", self._token_url, data=data, headers=headers)

    async def _refresh_token_impl(
        self,
        refresh_token: str,
    ) -> httpx.Response:
        """Refresh Google access token."""
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        headers = {"Accept": "application/json"}
        return await self._make_request("POST", self._token_url, data=data, headers=headers)

    async def get_user_info(self, token: Token) -> OAuthUser:
        """Get user information from Google.

        Args:
            token: Valid access token

        Returns:
            OAuthUser entity

        Raises:
            OAuthUserInfoError: If user info fetch fails
        """
        headers = {"Authorization": f"Bearer {token.access_token}"}

        try:
            response = await self._make_request("GET", self.GOOGLE_USERINFO_URL, headers=headers)

            if response.status_code != 200:
                raise OAuthUserInfoError(f"Failed to get Google user info: {response.status_code}")

            data = response.json()

            return OAuthUser(
                id=data.get("id", ""),
                email=data.get("email", ""),
                name=data.get("name"),
                avatar=data.get("picture"),
                provider=self.name,
                provider_id=data.get("id", ""),
            )

        except httpx.RequestError as e:
            raise OAuthUserInfoError(f"Failed to fetch Google user info: {e}") from e
