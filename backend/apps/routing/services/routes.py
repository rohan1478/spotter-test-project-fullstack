from django.conf import settings

from apps.routing.domain.checkpoints import sample_checkpoints
from apps.routing.domain.errors import RoutingError
from apps.routing.domain.geometry import METERS_PER_MILE
from apps.routing.domain.route_models import Place
from apps.routing.providers.geoapify import GeoapifyClient
from apps.routing.providers.mapbox import MapboxClient
from apps.routing.providers.timezones import timezone_at


def place_payload(place: Place) -> dict:
    return {"id": place.id, "label": place.label, "coordinate": place.coordinate, "timeZone": place.time_zone}


def geocoding_client():
    return GeoapifyClient(settings.GEOAPIFY_API_KEY, settings.PROVIDER_TIMEOUT_SECONDS)


def routing_client():
    return MapboxClient(settings.MAPBOX_ACCESS_TOKEN, settings.PROVIDER_TIMEOUT_SECONDS)


def search_places(query: str, limit: int = 5, *, geocoder=None) -> dict:
    matches = (geocoder or geocoding_client()).search(query, limit)
    return {
        "results": [place_payload(place) for place in matches],
        "requiresSelection": len(matches) > 1,
        "attribution": "Powered by Geoapify | © OpenStreetMap contributors",
    }


def _resolve_place(query, provided, field, geocoder, timezone_lookup):
    if provided:
        coordinate = tuple(provided["coordinate"])
        actual_zone = timezone_lookup(coordinate)
        if provided["timeZone"] != actual_zone:
            raise RoutingError(
                "location_timezone_mismatch", "Use the time zone returned by location search.",
                {"field": f"{field}Place.timeZone", "expectedTimeZone": actual_zone},
            )
        return Place(provided["id"], provided["label"], coordinate, actual_zone)
    matches = geocoder.search(query)
    if not matches:
        raise RoutingError("location_not_found", f"No location matched the {field}.", {"field": field})
    if len(matches) > 1:
        raise RoutingError("ambiguous_location", f"Choose a specific {field} from the search results.", {
            "field": field, "candidates": [place_payload(place) for place in matches],
        })
    return matches[0]


def get_route_options(trip: dict, *, geocoder=None, router=None, timezone_lookup=timezone_at) -> dict:
    geocoder = geocoder or geocoding_client()
    origin = _resolve_place(trip["origin"], trip.get("originPlace"), "origin", geocoder, timezone_lookup)
    if trip.get("departureTimeZone") and trip["departureTimeZone"] != origin.time_zone:
        raise RoutingError("location_timezone_mismatch", "Use the resolved origin's time zone.",
                           {"field": "departureTimeZone", "expectedTimeZone": origin.time_zone})
    destination = _resolve_place(trip["destination"], trip.get("destinationPlace"), "destination", geocoder, timezone_lookup)
    if origin.coordinate == destination.coordinate:
        raise RoutingError("identical_locations", "Origin and destination resolve to the same location.")
    candidates, warnings = (router or routing_client()).alternatives(origin.coordinate, destination.coordinate)
    routes = []
    for index, route in enumerate(candidates, 1):
        points = sample_checkpoints(
            route, trip["departure"], trip["spacing"], timezone_lookup,
            max_checkpoints=settings.ROUTING_MAX_CHECKPOINTS,
        )
        checkpoints = [{
            "id": f"{index:02d}-{point.number}", "number": point.number,
            "name": origin.label if position == 0 else destination.label if position == len(points)-1 else f"Mile {point.miles:g}",
            "coordinate": point.coordinate, "miles": point.miles,
            "arrival": point.arrival, "timeZone": point.time_zone,
            "elapsedMinutes": point.elapsed_seconds / 60,
        } for position, point in enumerate(points)]
        routes.append({
            "id": f"{index:02d}", "name": route.name, "highway": route.highway,
            "geometry": route.geometry, "distance": points[-1].miles,
            "providerDistance": route.distance_meters / METERS_PER_MILE,
            "duration": route.duration_seconds / 60, "checkpoints": checkpoints,
            "routingProfile": "mapbox/driving", "avoid": route.avoid,
        })
    return {
        "routes": routes, "resolvedPlaces": {"origin": place_payload(origin), "destination": place_payload(destination)},
        "departure": trip["departure"], "spacing": trip["spacing"],
        "distanceBasis": "wgs84-geodesic", "warnings": list(warnings),
    }
