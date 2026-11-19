"""Built-in licence and routing defaults for private hire (owner decision 16 Nov 2026).

The Owner decided Travelly handles this by itself: no Admin screen, nothing to set up by hand.
A service that has NO matrix saved (`settings['licence_compatibility']` absent) uses these by vehicle type.
A matrix saved through the Admin API (even an empty one) always wins, so the rule can still be tightened later.

DEMO VALUES, to be confirmed against the Department of Motor Traffic classes before going live:
B1 three-wheeler, B car or light van, D1 light bus, D bus. A D licence also covers a light bus.
"""

LICENCE_BY_VEHICLE_TYPE = {
    'CAR': ['B'],
    'VAN': ['B'],
    'THREE_WHEELER': ['B1'],
    'BUS': ['D1', 'D'],
}
ROUTING_BY_VEHICLE_TYPE = {
    'CAR': 'driving-car',
    'VAN': 'driving-car',
    'THREE_WHEELER': 'driving-car',
    'BUS': 'driving-hgv',
}


def accepted_licences(settings, vehicle):
    """Licence codes accepted for this vehicle, or None when no rule covers it."""
    saved = settings.get('licence_compatibility')
    if saved is not None:
        return saved.get((vehicle.verified_eligibility or {}).get('category'))
    return LICENCE_BY_VEHICLE_TYPE.get(vehicle.vehicle_type_code)


def routing_profile_for(settings, vehicle):
    saved = settings.get('routing_profiles')
    if saved is not None:
        return saved.get((vehicle.verified_eligibility or {}).get('category'))
    return ROUTING_BY_VEHICLE_TYPE.get(vehicle.vehicle_type_code)
