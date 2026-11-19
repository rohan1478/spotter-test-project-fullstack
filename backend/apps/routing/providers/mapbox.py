from math import fsum, isclose

from apps.routing.domain.errors import RoutingError
from apps.routing.domain.geometry import geometry_fingerprint, validate_coordinate
from apps.routing.domain.route_models import Coordinate, ProviderRoute
from apps.routing.domain.validation import require_nonnegative, require_positive

from .http import ProviderHTTPClient


class MapboxClient(ProviderHTTPClient):
    def __init__(self, api_key: str, timeout_seconds=15, transport=None):
        super().__init__("Mapbox", api_key, timeout_seconds, transport)

    def _request_routes(self, origin: Coordinate, destination: Coordinate, avoid=()) -> tuple[ProviderRoute, ...]:
        coordinates = ";".join(f"{lon},{lat}" for lon, lat in (origin, destination))
        params = {
            "access_token": self.api_key, "alternatives": "true", "overview": "full",
            "geometries": "geojson", "annotations": "distance,duration", "steps": "false",
        }
        if avoid:
            params["exclude"] = ",".join(avoid)
        body = self.get_json(f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}", params)
        if body.get("code") in ("NoRoute", "NoSegment"):
            raise self.error("no_route", "No road route could be found between these locations.")
        if body.get("code") != "Ok" or not isinstance(body.get("routes"), list):
            raise self.error("invalid_provider_response", "Mapbox returned invalid route data.")
        if not body["routes"]:
            raise self.error("no_route", "No road route could be found between these locations.")
        try:
            return tuple(self._parse_route(item, avoid) for item in body["routes"][:3])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise self.error("invalid_provider_response", "Mapbox returned misaligned or invalid route annotations.") from None

    def _parse_route(self, item: dict, avoid: tuple[str, ...]) -> ProviderRoute:
        if item["geometry"]["type"] != "LineString":
            raise ValueError("Expected road LineString.")
        geometry = tuple(validate_coordinate(point) for point in item["geometry"]["coordinates"])
        if len(geometry) < 2:
            raise ValueError("Route needs at least two points.")
        if all(point == geometry[0] for point in geometry):
            raise ValueError("Route geometry has no traveled distance.")
        distances, durations, summaries = [], [], []
        for leg in item["legs"]:
            distances.extend(leg["annotation"]["distance"])
            durations.extend(leg["annotation"]["duration"])
            summary = leg.get("summary", "")
            if not isinstance(summary, str):
                raise ValueError("Invalid road summary.")
            if summary:
                summaries.append(summary)
        if len(distances) != len(geometry) - 1 or len(durations) != len(distances):
            raise ValueError("Annotations do not align with full geometry.")
        for value in (*distances, *durations):
            require_nonnegative(value, "Road segment annotation")
        require_positive(item["distance"], "Route distance")
        require_positive(item["duration"], "Route duration")
        if not isclose(fsum(distances), item["distance"], rel_tol=.005, abs_tol=1):
            raise ValueError("Distance annotations do not cover the route.")
        if not isclose(fsum(durations), item["duration"], rel_tol=.005, abs_tol=1):
            raise ValueError("Duration annotations do not cover the route.")
        total_duration = fsum(durations)
        if total_duration <= 0:
            raise ValueError("Missing segment travel time.")
        durations = [duration * item["duration"] / total_duration for duration in durations]
        highway = ", ".join(summaries)
        return ProviderRoute(
            f"via {highway}" if highway else "Road route", highway, geometry,
            item["distance"], item["duration"], tuple(distances), tuple(durations), avoid,
        )

    def alternatives(self, origin: Coordinate, destination: Coordinate):
        origin, destination = validate_coordinate(origin), validate_coordinate(destination)
        routes, seen, warnings = [], set(), []
        for avoid in ((), ("toll",), ("motorway",)):
            try:
                candidates = self._request_routes(origin, destination, avoid)
            except RoutingError as error:
                if not routes:
                    raise
                if error.code == "no_route":
                    continue
                warnings.append({
                    "code": "alternatives_unavailable",
                    "message": "Additional alternatives could not be retrieved; available routes are retained.",
                })
                break
            for candidate in candidates:
                fingerprint = geometry_fingerprint(candidate.geometry)
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    routes.append(candidate)
                if len(routes) == 3:
                    break
            if len(routes) == 3:
                break
        if not routes:
            raise self.error("invalid_provider_response", "Mapbox returned empty road geometry.")
        if len(routes) < 3:
            warnings.append({"code": "fewer_route_options", "message": f"Found {len(routes)} distinct route option(s); three are not available."})
        if any(route.avoid for route in routes):
            warnings.append({"code": "alternative_constraints", "message": "Some alternatives avoid toll roads or motorways; each route lists its avoid constraints."})
        return tuple(routes), tuple(warnings)
