def test_public_search_query_params(client):
    assert client.get('/api/v1/routes?limit=100').status_code == 200
    assert client.get('/api/v1/scheduled-trips?min_seats=1&origin=Col').status_code == 200
    assert client.get('/api/v1/users/me?x=1').status_code in (401, 422)
