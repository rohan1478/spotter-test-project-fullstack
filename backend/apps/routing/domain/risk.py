from .choices import RISK_SCORES, RiskLevel
from .models import WeatherReading, WeatherRisk
from .validation import require_nonnegative, require_positive


def classify_wind(wind_mph: float) -> RiskLevel:
    require_nonnegative(wind_mph, "Wind")
    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 45:
        return RiskLevel.SEVERE
    if wind_mph >= 35:
        return RiskLevel.HIGH
    if wind_mph >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(rain_in_per_hour: float) -> RiskLevel:
    require_nonnegative(rain_in_per_hour, "Rain")
    if rain_in_per_hour > 1.0:
        return RiskLevel.NO_TRAVEL
    if rain_in_per_hour >= 0.50:
        return RiskLevel.SEVERE
    if rain_in_per_hour >= 0.25:
        return RiskLevel.HIGH
    if rain_in_per_hour >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(snow_in_per_hour: float) -> RiskLevel:
    require_nonnegative(snow_in_per_hour, "Snow")
    if snow_in_per_hour > 3.0:
        return RiskLevel.NO_TRAVEL
    if snow_in_per_hour >= 2.0:
        return RiskLevel.SEVERE
    if snow_in_per_hour >= 1.0:
        return RiskLevel.HIGH
    if snow_in_per_hour >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def assess_weather(weather: WeatherReading, load_weight_lb: float) -> WeatherRisk:
    require_positive(load_weight_lb, "Load weight")
    if not isinstance(weather, WeatherReading):
        raise ValueError("weather must be a WeatherReading.")
    wind = classify_wind(weather.wind_mph) if weather.wind_mph is not None else None
    rain = classify_rain(weather.rain_in_per_hour) if weather.rain_in_per_hour is not None else None
    snow = classify_snow(weather.snow_in_per_hour) if weather.snow_in_per_hour is not None else None
    reasons = []

    if weather.wind_mph is not None:
        if weather.wind_mph >= 55:
            reasons.append("Wind at or above 55 mph means No Travel for any load.")
        elif weather.wind_mph >= 45 and load_weight_lb > 30000:
            wind = RiskLevel.NO_TRAVEL
            reasons.append("Wind from 45 to below 55 mph with a load above 30,000 lb means No Travel.")
        elif 35 <= weather.wind_mph < 45 and load_weight_lb > 40000:
            wind = RiskLevel.SEVERE
            reasons.append("Wind from 35 to below 45 mph with a load above 40,000 lb means Severe risk.")
        elif wind != RiskLevel.LOW:
            reasons.append(f"Wind of {weather.wind_mph:g} mph has {wind.value} risk.")
    for name, value, risk in (
        ("Rain", weather.rain_in_per_hour, rain),
        ("Snow", weather.snow_in_per_hour, snow),
    ):
        if risk is not None and risk != RiskLevel.LOW:
            reasons.append(f"{name} of {value:g} in/hr has {risk.value} risk.")

    missing = [name for name, risk in (("wind", wind), ("rain", rain), ("snow", snow)) if risk is None]
    if missing:
        reasons.append(f"Missing required weather: {', '.join(missing)}.")
        combined = None
    else:
        combined = max((wind, rain, snow), key=RISK_SCORES.__getitem__)
        if not reasons:
            reasons.append("All weather conditions are Low risk.")
    return WeatherRisk(combined, wind, rain, snow, tuple(reasons))
