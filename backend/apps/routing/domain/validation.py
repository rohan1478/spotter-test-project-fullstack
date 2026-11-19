import math
from numbers import Real


def require_nonnegative(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite, nonnegative number.")
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite, nonnegative number.")


def require_positive(value: float, name: str) -> None:
    require_nonnegative(value, name)
    if value == 0:
        raise ValueError(f"{name} must be greater than zero.")
