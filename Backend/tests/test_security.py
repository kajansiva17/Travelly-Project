import time
from uuid import uuid4
import jwt
import pytest
from pydantic import ValidationError
from app.config import Settings, get_settings
from app.errors import ApiError
from app.schemas import RegisterRequest, phone_number
from app.security import hasher, verify_password, issue_tokens, decode_token


def test_password_hash_salt_and_parameters():
    first, second = hasher.hash('a secure travel passphrase'), hasher.hash('a secure travel passphrase')
    assert first != second and '$argon2id$' in first and 'm=65536,t=3,p=1' in first
    assert verify_password('a secure travel passphrase', first)
    assert not verify_password('wrong password', first)


@pytest.mark.parametrize('length,valid', [(11, False), (12, True), (128, True), (129, False)])
def test_password_boundaries(length, valid):
    data = {'full_name':'Test', 'email':'test@example.com', 'password':'Aa1!'+'x'*(length-4), 'phone_e164':'+94771234567', 'accept_terms':True}
    if valid:
        assert RegisterRequest(**data).password == data['password']
    else:
        with pytest.raises(ValidationError): RegisterRequest(**data)


def test_new_password_composition_without_normalization():
    data = {'full_name': 'Test', 'email': 'test@example.com', 'phone_e164': '+94771234567', 'accept_terms': True}
    for password in ['TravellyStrong1!', 'Aa1!' + '\u00e9' * 60, 'Aa1!' + '\U0001f600' * 100]:
        assert RegisterRequest(**data, password=password).password == password
    for password in ['  twelve 12 ', '\u00e9' * 12, '\U0001f600' * 12, 'Abcdefghijk1', 'Abcdefghijk!', 'ABCDEFGHIJ1!', 'abcdefghij1!', 'Aa1!' + 'x'*8 + '\n']:
        with pytest.raises(ValidationError): RegisterRequest(**data, password=password)


def test_postgres_database_and_application_identity_required():
    for url in ['sqlite:///local.db', 'postgresql+psycopg://postgres:secret@localhost/travelly_dev', 'postgresql+psycopg://travelly_app:secret@localhost/other_db']:
        with pytest.raises(ValidationError): Settings(database_url=url, jwt_secret='x'*40, jwt_refresh_secret='y'*40)


def test_jwt_type_signature_audience_expiry_and_lifetime():
    settings=get_settings()
    tokens,sid,expires=issue_tokens(uuid4(),settings)
    access=decode_token(tokens['access_token'],settings)
    refresh=decode_token(tokens['refresh_token'],settings,'refresh')
    assert access['sid']==refresh['sid']==sid and access['exp']-access['iat']==900
    assert refresh['exp']-refresh['iat']==604800
    assert 'email' not in access and 'roles' not in access
    with pytest.raises(ApiError): decode_token(tokens['refresh_token'],settings)
    claims={**access,'exp':int(time.time())-100}
    with pytest.raises(ApiError): decode_token(jwt.encode(claims,settings.jwt_secret,algorithm='HS256'),settings)
    claims={**access,'aud':'wrong-client'}
    with pytest.raises(ApiError): decode_token(jwt.encode(claims,settings.jwt_secret,algorithm='HS256'),settings)
    with pytest.raises(ApiError): decode_token(jwt.encode(access,'z'*40,algorithm='HS256'),settings)


def test_phone_requires_explicit_valid_international_number():
    assert phone_number('+94 77 123 4567')=='+94771234567'
    with pytest.raises(ValueError): phone_number('0771234567')
