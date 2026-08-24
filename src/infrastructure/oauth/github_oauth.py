"""GitHub OAuth Provider Implementation."""

from typing import Any, Dict, List, Optional

import httpx

from domain.auth.entities import OAuthUser, Token

from .base_oauth import BaseOAuthProvider, OAuthUserInfoError


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth 2.0 provider implementation."""

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

    @property
    def name(self) -> str:
        return "github"

    @property
    def display_name(self) -> str:
        return "GitHub"

    @property
    def _authorization_url(self) -> str:
        return self.GITHUB_AUTH_URL

    @property
    def _token_url(self) -> str:
        return self.GITHUB_TOKEN_URL

    def _get_authorization_params(self, state: str, redirect_uri: str) -> Dict[str, str]:
        """Build GitHub OAuth authorization parameters."""
        return {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
        }

    async def _exchange_code_impl(
        self,
        code: str,
        redirect_uri: str,
    ) -> httpx.Response:
        """Exchange authorization code for GitHub token."""
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
        }
        headers = {"Accept": "application/json"}
        return await self._make_request("POST", self._token_url, data=data, headers=headers)

    async def _refresh_token_impl(
        self,
        refresh_token: str,
    ) -> httpx.Response:
        """GitHub OAuth does not support token refresh."""
        raise NotImplementedError("GitHub OAuth does not support token refresh")

    async def get_user_info(self, token: Token) -> OAuthUser:
        """Get user information from GitHub.

        Args:
            token: Valid access token

        Returns:
            OAuthUser entity

        Raises:
            OAuthUserInfoError: If user info fetch fails
        """
        headers = {"Authorization": f"token {token.access_token}"}

        try:
            # Get user data
            response = await self._make_request("GET", self.GITHUB_USER_URL, headers=headers)

            if response.status_code != 200:
                raise OAuthUserInfoError(f"Failed to get GitHub user info: {response.status_code}")

            data = response.json()
            user_id = str(data.get("id", ""))
            login = data.get("login", "")
            name = data.get("name", login)
            avatar = data.get("avatar_url")

            # Get email from user data or emails endpoint
            email = data.get("email")
            if not email:
                email = await self._get_primary_email(token.access_token)

            if not email:
                raise OAuthUserInfoError("GitHub user has no email")

            return OAuthUser(
                id=user_id,
                email=email,
                name=name,
                avatar=avatar,
                provider=self.name,
                provider_id=user_id,
            )

        except httpx.RequestError as e:
            raise OAuthUserInfoError(f"Failed to fetch GitHub user info: {e}") from e

    async def _get_primary_email(self, access_token: str) -> Optional[str]:
        """Get primary email from GitHub."""
        headers = {"Authorization": f"token {access_token}"}

        try:
            response = await self._make_request("GET", self.GITHUB_EMAILS_URL, headers=headers)

            if response.status_code != 200:
                return None

            emails: List[Dict[str, Any]] = response.json()

            # Find primary email
            primary = next((e for e in emails if e.get("primary")), None)
            if primary:
                return primary.get("email")

            # Fallback to first verified email
            verified = next((e for e in emails if e.get("verified")), None)
            if verified:
                return verified.get("email")

            # Fallback to first email
            if emails:
                return emails[0].get("email")

            return None

        except Exception:
            return None
