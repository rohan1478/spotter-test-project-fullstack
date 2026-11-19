from dataclasses import dataclass

from .choices import RiskLevel
from .validation import require_nonnegative


@dataclass(frozen=True)
class WeatherReading:
    wind_mph: float | None
    rain_in_per_hour: float | None
    snow_in_per_hour: float | None

    def __post_init__(self):
        for name in ("wind_mph", "rain_in_per_hour", "snow_in_per_hour"):
            value = getattr(self, name)
            if value is not None:
                require_nonnegative(value, name)


@dataclass(frozen=True)
class CheckpointWeather:
    miles: float
    weather: WeatherReading

    def __post_init__(self):
        require_nonnegative(self.miles, "Checkpoint miles")
        if not isinstance(self.weather, WeatherReading):
            raise ValueError("Checkpoint weather must be a WeatherReading.")


@dataclass(frozen=True)
class WeatherRisk:
    risk: RiskLevel | None
    wind_risk: RiskLevel | None
    rain_risk: RiskLevel | None
    snow_risk: RiskLevel | None
    reasons: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.risk is not None


@dataclass(frozen=True)
class RiskInterval:
    start_miles: float
    end_miles: float
    risk: RiskLevel | None

    @property
    def distance_miles(self) -> float:
        return self.end_miles - self.start_miles


@dataclass(frozen=True)
class RiskExposure:
    risk: RiskLevel | None
    miles: float


@dataclass(frozen=True)
class RouteAssessment:
    route_id: str
    duration_minutes: float
    distance_miles: float
    checkpoints: tuple[WeatherRisk, ...]
    intervals: tuple[RiskInterval, ...]
    exposure: tuple[RiskExposure, ...]
    risk: RiskLevel | None
    average_risk: float | None

    def miles_at_risk(self, risk: RiskLevel | None) -> float:
        return next((item.miles for item in self.exposure if item.risk == risk), 0.0)

    @property
    def severe_miles(self) -> float:
        return self.miles_at_risk(RiskLevel.SEVERE)

    @property
    def high_miles(self) -> float:
        return self.miles_at_risk(RiskLevel.HIGH)

    @property
    def no_travel_miles(self) -> float:
        return self.miles_at_risk(RiskLevel.NO_TRAVEL)

    @property
    def unknown_miles(self) -> float:
        return self.miles_at_risk(None)

    @property
    def complete(self) -> bool:
        return all(checkpoint.complete for checkpoint in self.checkpoints)

    @property
    def eligible(self) -> bool:
        return self.complete and self.no_travel_miles == 0


@dataclass(frozen=True)
class RouteRecommendation:
    recommended_route_id: str | None
    ranked_route_ids: tuple[str, ...]
    excluded_route_ids: tuple[str, ...]
    explanation: str
