"""Licence and routing defaults: Travelly handles them itself unless Admin saved a matrix (owner decision 16 Nov 2026)."""
from types import SimpleNamespace

from app.services.hire_defaults import accepted_licences, routing_profile_for


def vehicle(kind, category=None):
    return SimpleNamespace(vehicle_type_code=kind, verified_eligibility={'category': category} if category else {})


def test_a_service_without_a_saved_matrix_uses_the_built_in_defaults_by_vehicle_type():
    assert accepted_licences({}, vehicle('VAN')) == ['B']
    assert accepted_licences({}, vehicle('THREE_WHEELER')) == ['B1']
    assert accepted_licences({}, vehicle('BUS')) == ['D1', 'D']
    assert routing_profile_for({}, vehicle('VAN')) == 'driving-car'
    assert routing_profile_for({}, vehicle('BUS')) == 'driving-hgv'
    assert accepted_licences({}, vehicle('SPACESHIP')) is None   # an unknown type is never guessed


def test_a_matrix_saved_by_admin_always_wins_even_when_empty():
    saved = {'licence_compatibility': {'MINIBUS': ['D1']}, 'routing_profiles': {'MINIBUS': 'driving-hgv'}}
    assert accepted_licences(saved, vehicle('VAN', 'MINIBUS')) == ['D1']
    assert routing_profile_for(saved, vehicle('VAN', 'MINIBUS')) == 'driving-hgv'
    assert accepted_licences(saved, vehicle('VAN', 'OTHER')) is None   # not in the saved matrix: denied, no fallback
    assert accepted_licences({'licence_compatibility': {}}, vehicle('VAN')) is None
