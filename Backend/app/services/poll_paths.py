def is_poll(method, path):
    """Background refreshes (notifications, Book now requests, chat, live vehicles) are light read-only GETs.
    They are not counted by the rate limits; login, OTP, booking and payment keep their strict limits."""
    if method != 'GET':
        return False
    if path in ('/api/v1/notifications', '/api/v1/me/ride-requests', '/api/v1/me/live-vehicles'):
        return True
    parts = path.strip('/').split('/')
    return len(parts) == 5 and parts[:3] == ['api', 'v1', 'bookings'] and parts[4] in ('messages', 'contacts')
