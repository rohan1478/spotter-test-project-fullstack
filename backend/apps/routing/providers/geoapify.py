from apps.routing.domain.geometry import validate_coordinate
from apps.routing.domain.route_models import Place

from .http import ProviderHTTPClient
from .timezones import timezone_at


class GeoapifyClient(ProviderHTTPClient):
    def __init__(self, api_key: str, timeout_seconds=15, transport=None, timezone_lookup=timezone_at):
        super().__init__("Geoapify", api_key, timeout_seconds, transport)
        self.timezone_lookup = timezone_lookup

    def search(self, text: str, limit: int = 5) -> tuple[Place, ...]:
        body = self.get_json("https://api.geoapify.com/v1/geocode/search", {
            "text": text, "format": "json", "limit": limit, "apiKey": self.api_key,
        })
        results = body.get("results")
        if not isinstance(results, list):
            raise self.error("invalid_provider_response", "Geoapify returned invalid location results.")
        places, seen = [], set()
        try:
            for item in results[:limit]:
                coordinate = validate_coordinate([item["lon"], item["lat"]])
                identifier, label = item["place_id"], item["formatted"]
                if not isinstance(identifier, str) or not identifier or len(identifier) > 200:
                    raise ValueError("Invalid place ID.")
                if not isinstance(label, str) or not label.strip():
                    raise ValueError("Invalid place label.")
                if identifier in seen:
                    continue
                seen.add(identifier)
                places.append(Place(identifier, label, coordinate, self.timezone_lookup(coordinate)))
        except (KeyError, TypeError, ValueError):
            raise self.error("invalid_provider_response", "Geoapify returned malformed location data.") from None
        return tuple(places)
