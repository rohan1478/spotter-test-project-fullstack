import httpx

from apps.routing.domain.errors import RoutingError


class ProviderHTTPClient:
    def __init__(self, provider: str, api_key: str, timeout_seconds: float = 15, transport=None, *, requires_api_key=True):
        self.provider = provider
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.requires_api_key = requires_api_key

    def error(self, code: str, message: str) -> RoutingError:
        return RoutingError(code, message, {"provider": self.provider})

    def get_json(self, url: str, params: dict, *, allow_list=False) -> dict | list:
        if self.requires_api_key and not self.api_key.strip():
            raise self.error("provider_not_configured", f"{self.provider} credentials are not configured.")
        try:
            with httpx.Client(
                timeout=self.timeout_seconds, transport=self.transport,
                follow_redirects=False, trust_env=False,
            ) as client:
                response = client.get(url, params=params)
        except httpx.TimeoutException:
            raise self.error("provider_timeout", f"{self.provider} did not respond in time.") from None
        except httpx.RequestError:
            raise self.error("provider_unavailable", f"{self.provider} could not be reached.") from None
        if response.status_code in (401, 403):
            raise self.error("provider_authentication_error", f"{self.provider} rejected its configured credentials.")
        if response.status_code == 429:
            raise self.error("provider_rate_limited", f"{self.provider} request quota was reached. Try again later.")
        if response.status_code >= 500:
            raise self.error("provider_unavailable", f"{self.provider} is temporarily unavailable.")
        if response.status_code != 200:
            raise self.error("provider_rejected_request", f"{self.provider} could not process this request.")
        if len(response.content) > 8 * 1024 * 1024:
            raise self.error("invalid_provider_response", f"{self.provider} returned an oversized response.")
        try:
            result = response.json()
        except ValueError:
            raise self.error("invalid_provider_response", f"{self.provider} returned invalid JSON.") from None
        if not isinstance(result, dict) and not (allow_list and isinstance(result, list)):
            raise self.error("invalid_provider_response", f"{self.provider} returned an invalid response.")
        return result
