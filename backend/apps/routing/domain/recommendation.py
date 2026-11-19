from collections.abc import Sequence

from .models import RouteAssessment, RouteRecommendation


def _ranking_key(route: RouteAssessment) -> tuple[float, float, float, float, str]:
    if route.average_risk is None:
        raise ValueError("An incomplete route cannot be ranked.")
    return (
        route.severe_miles,
        route.high_miles,
        route.average_risk,
        route.duration_minutes,
        route.route_id,
    )


def _explain_winner(winner: RouteAssessment, runner_up: RouteAssessment) -> str:
    metrics = (
        (winner.severe_miles, runner_up.severe_miles, "Severe-risk miles", "mi"),
        (winner.high_miles, runner_up.high_miles, "High-risk miles", "mi"),
        (winner.average_risk, runner_up.average_risk, "distance-weighted average risk", ""),
        (winner.duration_minutes, runner_up.duration_minutes, "travel time", "min"),
    )
    for value, other, label, unit in metrics:
        if value != other:
            suffix = f" {unit}" if unit else ""
            return (
                f"Route {winner.route_id} is recommended for lower {label} "
                f"({value:g}{suffix} versus {other:g}{suffix} on route {runner_up.route_id}). "
                "Weather risk is compared before travel time."
            )
    return (
        f"Routes tie on Severe miles, High miles, average risk, and travel time. "
        f"Route {winner.route_id} is selected by route ID for a stable result."
    )


def recommend_routes(routes: Sequence[RouteAssessment]) -> RouteRecommendation:
    routes = tuple(routes)
    if any(not isinstance(route, RouteAssessment) for route in routes):
        raise ValueError("Supply RouteAssessment values produced by assess_route().")
    ids = [route.route_id for route in routes]
    if len(ids) != len(set(ids)):
        raise ValueError("Route IDs must be unique.")
    eligible = sorted((route for route in routes if route.eligible), key=_ranking_key)
    excluded = tuple(sorted(route.route_id for route in routes if not route.eligible))
    if not eligible:
        explanation = (
            "No routes were supplied."
            if not routes
            else "No route can be recommended: every route has No Travel exposure or incomplete weather."
        )
        return RouteRecommendation(None, (), excluded, explanation)
    winner = eligible[0]
    explanation = (
        f"Route {winner.route_id} is the only route with complete weather and no No Travel miles."
        if len(eligible) == 1
        else _explain_winner(winner, eligible[1])
    )
    return RouteRecommendation(winner.route_id, tuple(route.route_id for route in eligible), excluded, explanation)
