"""Upload optionality is separate from the existing role-approval evidence gate."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.review_api import UploadMetadata, upload_metadata_error
from conftest import signed_in, bearer

TYPES = ('NIC', 'PASSPORT', 'DRIVING_LICENCE', 'VEHICLE_REGISTRATION', 'OWNER_AUTHORISATION')


@pytest.mark.parametrize('kind', TYPES)
def test_frozen_optional_upload_metadata(kind):
    meta = UploadMetadata(owner_type='USER', owner_id=str(uuid4()), document_type=kind)
    assert meta.number is meta.issuing_country is meta.issue_date is meta.expiry_date is None


@pytest.mark.parametrize('metadata,field,message', [
    ({'number': ' '}, 'number', '1–100'),
    ({'number': 'x' * 101}, 'number', '1–100'),
    ({'issuing_country': 'ZZ'}, 'issuing_country', 'country that issued'),
    ({'issuing_country': 'lk'}, 'issuing_country', 'country that issued'),
    ({'issue_date': '2026-02-30'}, 'issue_date', 'valid date'),
    ({'expiry_date': '2026-1-01'}, 'expiry_date', 'valid date'),
    ({'issue_date': '2026-10-20', 'expiry_date': '2026-10-19'}, 'expiry_date', 'on or after'),
    ({'document_type': 'SECRET_UNSUPPORTED_TYPE'}, 'document_type', 'supported document type'),
    ({'SECRET_UNKNOWN_FIELD': 'secret-value'}, 'request', 'unsupported'),
])
def test_field_specific_errors_are_safe(metadata, field, message):
    values = {'owner_type': 'USER', 'owner_id': str(uuid4()), 'document_type': 'NIC', **metadata}
    with pytest.raises(ValidationError) as caught:
        UploadMetadata.model_validate(values)
    error = upload_metadata_error(caught.value)
    assert error.status == 422
    assert error.fields[0]['field'] == field
    assert message in error.fields[0]['message']
    assert 'SECRET' not in str(error.fields) and 'secret-value' not in str(error.fields)


def test_valid_country_number_and_date_boundaries():
    meta = UploadMetadata(owner_type='USER', owner_id=str(uuid4()), document_type='DRIVING_LICENCE',
                          number='  REF 123  ', issuing_country='GB', issue_date='2026-10-26', expiry_date='2026-10-26')
    assert meta.number == 'REF 123'
    # Foreign licence upload remains allowed; it still cannot satisfy Driver approval.
    assert meta.issuing_country == 'GB'
    assert meta.issue_date == meta.expiry_date


def test_http_upload_returns_inline_metadata_errors(client, passenger):
    person, tokens = signed_in(client, passenger)
    fields = {'owner_type': 'USER', 'owner_id': person['id'], 'document_type': 'NIC'}
    for extra, field in [({'number': ' '}, 'number'), ({'issuing_country': 'ZZ'}, 'issuing_country'),
                         ({'issue_date': '2026-02-30'}, 'issue_date'),
                         ({'issue_date': '2026-10-26', 'expiry_date': '2026-10-25'}, 'expiry_date')]:
        result = client.post('/api/v1/documents', data={**fields, **extra},
                             files={'file': ('document.png', b'not reached before metadata validation', 'image/png')}, headers=bearer(tokens))
        assert result.status_code == 422, result.text
        assert result.json()['field_errors'][0]['field'] == field
