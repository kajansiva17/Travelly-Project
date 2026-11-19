"""HeiGIT moved openrouteservice to api.heigit.org and shut down api.openrouteservice.org on 2-6 Nov 2026."""
import httpx
import pytest
from app.core.config import get_settings
from app.services.rate_locations import RateLocations
from app.services.hire_routing import ROUTE_TIMEOUT, route_post


class Reply:
    def __init__(self, body): self.body = body
    def raise_for_status(self): pass
    def json(self): return self.body


def test_location_search_uses_the_heigit_pelias_endpoint(monkeypatch):
    monkeypatch.setenv('ROUTING_API_KEY', 'test-key')
    seen = {}

    def fake_get(url, **kwargs):
        seen['url'], seen['headers'] = url, kwargs['headers']
        return Reply({'features': [{'geometry': {'coordinates': [79.85, 6.93]}, 'properties': {'label': 'Colombo Fort'}}]})
    monkeypatch.setattr(httpx, 'get', fake_get)
    found = RateLocations(get_settings()).search('Colombo')
    assert seen['url'] == 'https://api.heigit.org/pelias/v1/search'
    assert seen['headers'] == {'Authorization': 'test-key'}
    assert found['items'][0]['label'] == 'Colombo Fort'


def test_the_routing_base_url_can_move_again_without_code_changes(monkeypatch):
    monkeypatch.setenv('ROUTING_API_KEY', 'test-key')
    monkeypatch.setenv('ROUTING_BASE_URL', 'https://routing.example.test/')
    seen = {}
    monkeypatch.setattr(httpx, 'get', lambda url, **kwargs: seen.setdefault('url', url) and Reply({'features': []}))
    RateLocations(get_settings()).search('Kandy')
    assert seen['url'] == 'https://routing.example.test/pelias/v1/search'


def test_no_code_still_calls_the_retired_host():
    import pathlib
    for path in pathlib.Path('app').rglob('*.py'):
        assert 'https://api.openrouteservice.org' not in path.read_text(encoding='utf-8'), path


def test_route_call_retries_one_transient_transport_failure_with_bounded_timeouts(monkeypatch):
    settings = type('Settings', (), {'routing_base_url': 'https://routing.example.test', 'routing_api_key': 'test-key'})()
    calls = []
    reply = httpx.Response(200, request=httpx.Request('POST', 'https://routing.example.test/route'),
                           json={'features': []})

    def post(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 1:
            raise httpx.ConnectTimeout('temporary connection timeout')
        return reply

    monkeypatch.setattr(httpx, 'post', post)
    monkeypatch.setattr('app.services.hire_routing.time.sleep', lambda _seconds: None)
    assert route_post(settings, '/route', {'coordinates': []}) is reply
    assert len(calls) == 2
    assert all(call[1]['timeout'] == ROUTE_TIMEOUT for call in calls)
    assert all(call[1]['headers'] == {'Authorization': 'test-key'} for call in calls)


def test_route_call_does_not_retry_an_unroutable_provider_response(monkeypatch):
    settings = type('Settings', (), {'routing_base_url': 'https://routing.example.test', 'routing_api_key': 'test-key'})()
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return httpx.Response(404, request=httpx.Request('POST', url),
                              json={'error': {'code': 2010, 'message': 'Could not find routable point within 350 metres.'}})

    monkeypatch.setattr(httpx, 'post', post)
    with pytest.raises(httpx.HTTPStatusError):
        route_post(settings, '/route', {'coordinates': []})
    assert len(calls) == 1
