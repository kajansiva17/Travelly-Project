"""A saved booking's worked-out hours must not become a strict window for the next vehicle check (Owner confirm failed with
'Route travel falls outside the booked service hours' when a slower vehicle re-measured the route)."""
from uuid import uuid4
from app.schemas.hire_schemas import Itinerary
from test_rates import rate_owner  # noqa: F401
from test_hire_pricing import hire_setup  # noqa: F401


def saved(c):
    itin = c.itinerary(); itin['service_hours'] = ['6.77']
    return itin


def test_stored_itinerary_is_read_as_worked_out_hours(hire_setup):
    raw = saved(hire_setup)
    assert Itinerary.model_validate(raw)._auto is False      # typed hours stay strict
    assert Itinerary.stored(raw)._auto is True               # saved, worked-out hours are decided again by the vehicle's own route
    assert [str(h) for h in Itinerary.stored(raw).service_hours] == ['6.77']


def test_event_package_hours_stay_strict(hire_setup):
    raw = saved(hire_setup); raw['event_package_id'] = str(uuid4())
    assert Itinerary.stored(raw)._auto is False
