"""Explicit catalogue scope; never infer approved formulas from a service name."""
from app.core.errors import ApiError


def long_distance(service):
    return service is not None and service.category == 'PRIVATE_HIRE' and service.settings.get('pricing_scope') == 'LONG_DISTANCE'


def require_long_distance(service):
    if not long_distance(service):
        raise ApiError(409, 'PRICING_POLICY_NOT_APPROVED', 'Long-distance pricing requires an explicitly classified Long-distance service. Local, Airport and Event pricing rules are not available yet.')
