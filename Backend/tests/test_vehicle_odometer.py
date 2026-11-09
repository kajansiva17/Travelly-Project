"""Regression: saving vehicle facts that include the odometer must work (it was rejected with VEHICLE_FACTS_INVALID)."""
from decimal import Decimal
from uuid import uuid4
import pytest
from conftest import bearer
from test_vehicles import FACTS, actors, call  # noqa: F401  (actors is a fixture)


def new_draft(client, a):
    response = call(client, a, 'owner', 'post', '/vehicles', {'registration_number': 'TEST-' + uuid4().hex[:10]})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize('odometer', ['3', '120345.5', '0'])
def test_facts_with_odometer_save_and_second_edit_still_works(client, actors, odometer):
    row = new_draft(client, actors)
    body = {'expected_version': row['version'], **FACTS, 'current_odometer_km': odometer, 'transmission_type': 'Automatic',
            'air_conditioned': True, 'description': None}
    saved = call(client, actors, 'owner', 'patch', '/vehicles/' + row['id'], body)
    assert saved.status_code == 200, saved.text
    assert Decimal(saved.json()['current_odometer_km']) == Decimal(odometer)
    # Editing another fact afterwards merges the stored odometer back through validation.
    again = call(client, actors, 'owner', 'patch', '/vehicles/' + row['id'],
                 {'expected_version': saved.json()['version'], 'colour': 'Blue'})
    assert again.status_code == 200, again.text
    assert Decimal(again.json()['current_odometer_km']) == Decimal(odometer)


def test_bad_odometer_is_still_rejected_with_the_field_named(client, actors):
    row = new_draft(client, actors)
    for bad in ('-1', '1.25', 'abc', 12):
        response = call(client, actors, 'owner', 'patch', '/vehicles/' + row['id'],
                        {'expected_version': row['version'], 'current_odometer_km': bad})
        assert response.status_code == 422, (bad, response.text)
