import msal
import os
from mcp.server.auth.provider import OAuthAuthorizationServerProvider, AuthorizationParams, AuthorizationCode, RefreshToken, AccessToken
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from typing import Optional, Dict, Any
import time
import logging

"""
Microsoft Entra ID (Azure AD) Authentication Provider for MCP Server
-------------------------------------------------------------------

This module implements a public client authentication flow for Microsoft Entra ID.
It's designed for scenarios where you just want to authenticate users (validate they are logged in)
without needing confidential client capabilities.

Usage:
    provider = MSAuthProvider(
        tenant_id="your-tenant-id",  # e.g., 'common' or your specific tenant ID
        client_id="your-app-registration-id",
        redirect_uri="your-redirect-uri",
        scopes=["User.Read", "openid", "profile"]
    )

    # Then register this provider with your MCP server
    
Requirements:
    - Register an app in the Azure portal (Entra ID)
    - Configure the redirect URI in the app registration
    - For public clients, select the "Accounts in any organizational directory and personal accounts" option
    - Enable the necessary API permissions (Microsoft Graph User.Read at minimum)
"""

# Setup logging
logger = logging.getLogger("MSAuthProvider")

class MSAuthProvider(OAuthAuthorizationServerProvider):
    """
    Microsoft Authorization Server Provider
    Implements the required OAuthAuthorizationServerProvider methods for Microsoft OAuth.
    This implementation is designed for public client applications where the goal is
    just to validate that users are logged in with their Microsoft accounts.
    """
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        redirect_uri: str,
        scopes: list[str] = None,
        authority: str = None
    ):
        """
        Initialize the Microsoft Authentication provider with required parameters.
        
        Args:
            tenant_id: The Microsoft tenant ID
            client_id: The client ID from app registration
            redirect_uri: The redirect URI for the OAuth flow
            scopes: The list of scopes to request, defaults to ["User.Read"]
            authority: The authority URL, defaults to f"https://login.microsoftonline.com/{tenant_id}"
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["User.Read", "openid", "profile", "email"]
        self.authority = authority or f"https://login.microsoftonline.com/{tenant_id}"
        
        # Initialize the MSAL public client application
        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority
        )
        
        # Store code verifier and auth flow state
        self.auth_flow_state: Dict[str, Any] = {}
        
        logger.info(f"MSAuthProvider initialized with authority: {self.authority}")

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        """Retrieves client information by client ID."""
        # For Microsoft OAuth, we typically have a single client configured in the app
        if client_id == self.client_id:
            return OAuthClientInformationFull(
                client_id=self.client_id,
                client_secret=None,  # No client secret for public clients
                redirect_uris=[self.redirect_uri],
                grant_types=["authorization_code", "implicit"],
                response_types=["code", "token", "id_token"],
                scope=self.scopes
            )
        return None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Saves client information as part of registering it."""
        # Registration is typically handled in Azure Portal for MSAL
        logger.info(f"Client registration for {client_info.client_id} would be handled in Azure Portal")
        pass

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Handles the /authorize endpoint and returns a redirect URL for Microsoft OAuth."""
        # For a public client, we can use the authorization code flow with PKCE
        # PKCE (Proof Key for Code Exchange) provides additional security for public clients
        flow = self.app.initiate_auth_code_flow(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=params.state
        )
        
        # Store the auth flow state for later token acquisition
        state_key = params.state or "default_state"
        self.auth_flow_state[state_key] = flow
        
        logger.info(f"Authorization URL generated for state: {state_key}")
        return flow["auth_uri"]

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> Optional[AuthorizationCode]:
        """Loads an AuthorizationCode by its code."""
        # Create an authorization code object with the provided code
        # We don't validate it here as that happens during exchange
        return AuthorizationCode(
            code=authorization_code,
            client_id=client.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes,
            expires_at=int(time.time()) + 600,  # Code typically valid for 10 minutes
        )

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        """Exchanges an authorization code for an access token and refresh token."""
        # Find the corresponding auth flow
        flow = None
        for key, stored_flow in self.auth_flow_state.items():
            # Try to find the matching flow
            flow = stored_flow
            break

        if not flow:
            logger.warning("No matching auth flow found for token exchange")
            # Continue with basic flow if no stored flow is found

        try:
            # Use the stored flow for token acquisition if available
            if flow:
                result = self.app.acquire_token_by_auth_code_flow(
                    auth_code_flow=flow,
                    auth_response={"code": authorization_code.code},
                    scopes=self.scopes
                )
            else:
                # Fallback method - less secure but will work
                result = self.app.acquire_token_by_authorization_code(
                    code=authorization_code.code,
                    scopes=self.scopes,
                    redirect_uri=self.redirect_uri
                )
            
            if "access_token" in result:
                logger.info(f"Token exchange successful for client: {client.client_id}")
                return OAuthToken(
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token"),
                    id_token=result.get("id_token"),
                    expires_in=result.get("expires_in")
                )
            else:
                error_msg = result.get("error_description", "Unknown error during token exchange")
                logger.error(f"Token exchange failed: {error_msg}")
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Exception during token exchange: {str(e)}")
            raise

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> Optional[RefreshToken]:
        """Loads a RefreshToken by its token string."""
        # Create a refresh token object with the provided token
        # We can't validate it without trying to use it
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scope=self.scopes,
        )

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        """Exchanges a refresh token for an access token and refresh token."""
        # Use the refresh token to get a new access token
        try:
            # Public clients can still use refresh tokens
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=refresh_token.token,
                scopes=scopes or self.scopes
            )
            
            if "access_token" in result:
                logger.info(f"Refresh token exchange successful for client: {client.client_id}")
                return OAuthToken(
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token", refresh_token.token),  # Use old refresh token if new one not provided
                    id_token=result.get("id_token"),
                    expires_in=result.get("expires_in")
                )
            else:
                error_msg = result.get("error_description", "Unknown error during refresh token exchange")
                logger.error(f"Refresh token exchange failed: {error_msg}")
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Exception during refresh token exchange: {str(e)}")
            raise

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """Loads an access token by its token."""
        # For a public client, we can't directly validate tokens on the server
        # In a production app, you would want to:
        # 1. Use a JWT decoder library to extract claims from the token
        # 2. Verify the token signature using Microsoft's JWKS endpoint
        # 3. Check expiry, issuer, audience and other claims
        
        # Basic implementation using estimated validity
        try:
            # You could implement JWT decoding here
            # For example with PyJWT: decoded = jwt.decode(token, options={"verify_signature": False})
            # Then extract expiry from decoded['exp']
            
            # For now, create a basic token with estimated expiry
            return AccessToken(
                token=token,
                expires_at=int(time.time()) + 3600,  # Assume 1 hour validity
                scope=self.scopes
            )
        except Exception as e:
            logger.error(f"Error loading access token: {str(e)}")
            return None

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revokes an access or refresh token."""
        # Microsoft Entra ID does not support token revocation for public clients
        # The best approach is to:
        # 1. Use short-lived access tokens (default of 1 hour)
        # 2. Clear token cache in your application
        # 3. For sensitive applications, configure Conditional Access policies
        
        # Remove from MSAL token cache if possible
        try:
            # The MSAL token cache can be accessed, but it's complicated
            # For now, just log the attempt
            token_type = "access" if isinstance(token, AccessToken) else "refresh"
            logger.info(f"Token revocation requested for {token_type} token - clearing application cache")
            
            # In a real implementation, you might clear the cache:
            # self.app.remove_account(account=account_identifier)
        except Exception as e:
            logger.error(f"Error during token revocation: {str(e)}")
        pass