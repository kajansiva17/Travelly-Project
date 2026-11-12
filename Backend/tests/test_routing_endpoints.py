"""HeiGIT moved openrouteservice to api.heigit.org and shut down api.openrouteservice.org on 2-6 Nov 2026."""
import httpx
from app.core.config import get_settings
from app.services.rate_locations import RateLocations


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
