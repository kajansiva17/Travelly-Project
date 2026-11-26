"""Server-validated locations. Opaque proofs authorize coordinates, never accounts."""
import base64
import hashlib
import hmac
import json
from decimal import Decimal
import httpx
from app.core.errors import ApiError


class RateLocations:
    def __init__(self, settings):
        self.settings = settings
        self.key = hmac.new(settings.jwt_secret.encode(), b'travelly-location-proof-v1', hashlib.sha256).digest()

    def signed(self, label, latitude, longitude):
        payload = {'label': label, 'latitude': str(Decimal(str(latitude))), 'longitude': str(Decimal(str(longitude)))}
        encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).decode().rstrip('=')
        signature = hmac.new(self.key, encoded.encode(), hashlib.sha256).hexdigest()
        return {**payload, 'token': encoded + '.' + signature}

    def verify(self, place):
        try:
            encoded, signature = place.token.split('.')
            expected = hmac.new(self.key, encoded.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected): raise ValueError()
            data = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
            if data['label'] != place.label or Decimal(data['latitude']) != place.latitude or Decimal(data['longitude']) != place.longitude:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ApiError(422, 'INVALID_LOCATION', 'Select each route location from location search again.') from None

    def search(self, query):
        if not self.settings.routing_api_key:
            raise ApiError(503, 'ROUTING_NOT_CONFIGURED', 'Location search is not available yet. Please try again later.')
        try:
            # Fixed provider endpoint, server-only credential, no user-selected URL.
            response = httpx.get(self.settings.routing_base_url.rstrip('/') + '/pelias/v1/search',
                headers={'Authorization': self.settings.routing_api_key},
                params={'text': query, 'boundary.country': 'LK', 'size': 5}, timeout=10)
            response.raise_for_status()
            items = []
            for feature in response.json()['features'][:5]:
                lon, lat = feature['geometry']['coordinates']
                label = feature['properties']['label'][:200]
                if not -90 <= lat <= 90 or not -180 <= lon <= 180: raise ValueError()
                items.append(self.signed(label, lat, lon))
            return {'items': items, 'attribution': 'openrouteservice / OpenStreetMap contributors'}
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError):
            raise ApiError(503, 'ROUTING_UNAVAILABLE', 'Location search is temporarily unavailable. Please try again.') from None

    def reverse(self, latitude, longitude):
        """A pin on the map or the phone's position becomes a signed place. The label is the nearest named place the provider knows."""
        if not (5.5 <= latitude <= 10.2 and 79.3 <= longitude <= 82.2):
            raise ApiError(422, 'VALIDATION_ERROR', 'Choose a place inside Sri Lanka.')
        if not self.settings.routing_api_key:
            raise ApiError(503, 'ROUTING_NOT_CONFIGURED', 'Location search is not available yet. Please try again later.')
        try:
            response = httpx.get(self.settings.routing_base_url.rstrip('/') + '/pelias/v1/reverse',
                headers={'Authorization': self.settings.routing_api_key},
                params={'point.lat': latitude, 'point.lon': longitude, 'boundary.country': 'LK', 'size': 1}, timeout=10)
            response.raise_for_status()
            features = response.json()['features']
            label = features[0]['properties']['label'][:200] if features else ''
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
            raise ApiError(503, 'ROUTING_UNAVAILABLE', 'Location search is temporarily unavailable. Please try again.') from None
        return {'items': [self.signed(label or f'Pinned place ({latitude:.5f}, {longitude:.5f})', round(latitude, 6), round(longitude, 6))], 'attribution': 'openrouteservice / OpenStreetMap contributors'}
