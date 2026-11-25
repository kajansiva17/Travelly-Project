"""When the people on a booking may call each other: from `contact_hours_before` hours before the booking starts (Admin sets it per service in
service_types.settings, default 2 hours, 0 to 168). A Book now trip starts at once, so its numbers show at once."""
DEFAULT_CONTACT_HOURS = 2
MAX_CONTACT_HOURS = 168


def contact_hours(service):
    value = (service.settings or {}).get('contact_hours_before', DEFAULT_CONTACT_HOURS) if service is not None else DEFAULT_CONTACT_HOURS
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_CONTACT_HOURS else DEFAULT_CONTACT_HOURS
