"""Decimal pricing authority; no I/O or browser-supplied live-route trust."""
from decimal import Decimal, ROUND_HALF_UP
from app.schemas.rate_schemas import RateRule, ExampleTrip

ZERO = Decimal('0')


def calculate(rule: RateRule, trip: ExampleTrip):
    lines = []
    exclusions = []

    def line(code, label, quantity, rate, credit=False):
        value = quantity * rate
        lines.append({'code': code, 'label': label, 'quantity': str(quantity), 'rate': str(rate), 'amount': str(value), 'kind': 'CREDIT' if credit else 'CHARGE'})

    included = rule.included_km
    charged_hour_starts = {}
    reserved_hours = []
    if rule.method == 'DISTANCE':
        line('BASE', 'Base charge including stated km', Decimal('1'), rule.base_charge)
        line('EXTRA_KM', 'Distance beyond included km', max(ZERO, trip.distance_km - rule.included_km), rule.extra_km_rate)
    elif rule.method == 'FIXED_ROUTE':
        line('FIXED', 'Covered fixed-route fare', Decimal('1'), rule.fixed_fare)
    else:
        if trip.waiting_minutes and not trip.waiting_periods:
            raise ValueError('For day hire, enter the waiting periods so overlapping service time is charged only once.')
        included = ZERO
        for day, hours in enumerate(trip.service_hours):
            allowance = rule.included_hours_per_day
            partial = day > 0 and hours < allowance and hours * rule.extra_hour_rate < rule.day_charge
            if partial:
                line(f'DAY_{day+1}', f'Day {day+1}: partial package hours', hours, rule.extra_hour_rate)
                included += rule.included_km_per_day * hours / allowance
                charged_hour_starts[day] = ZERO
                reserved_hours.append(hours)
            else:
                line(f'DAY_{day+1}', f'Day {day+1}: full package', Decimal('1'), rule.day_charge)
                included += rule.included_km_per_day
                line(f'EXTRA_HOURS_{day+1}', f'Day {day+1}: service hours beyond package', max(ZERO, hours - allowance), rule.extra_hour_rate)
                charged_hour_starts[day] = allowance
                reserved_hours.append(max(hours, allowance))
        line('EXTRA_KM', 'Distance beyond pooled included km', max(ZERO, trip.distance_km - included), rule.extra_km_rate)
        line('OVERNIGHT', 'Agreed overnight Driver stays', Decimal(trip.overnight_stays), rule.overnight_driver_cost)
    if rule.method != 'FIXED_ROUTE':
        line('NIGHT_KM', 'All planned night km (22:00-05:00 Asia/Colombo)', trip.night_km, rule.night_km_rate)
    line('WAIT', 'Waiting beyond the free booking allowance (hours)', max(ZERO, trip.waiting_minutes - rule.free_wait_minutes) / Decimal('60'), rule.waiting_hour_rate)
    if rule.method == 'DAY_HIRE':
        free = rule.free_wait_minutes
        overlapping_hours = ZERO
        for period in sorted(trip.waiting_periods, key=lambda p: (p.day, p.start_hour)):
            skipped = min(free, period.minutes); free -= skipped
            start = period.start_hour + skipped / Decimal('60')
            end = period.start_hour + period.minutes / Decimal('60')
            overlapping_hours += max(ZERO, end - max(start, charged_hour_starts[period.day]))
        line('WAIT_OVERLAP', 'Already covered by overlapping service-time charge', overlapping_hours,
             min(rule.waiting_hour_rate, rule.extra_hour_rate), credit=True)
    if rule.return_to_base == 'SEPARATE_FIXED':
        line('RETURN_TO_BASE', rule.return_to_base_notes, Decimal('1'), rule.return_to_base_charge)
    for label, treatment in [('Tolls', rule.tolls), ('Parking', rule.parking)] + [(x.label, x.treatment) for x in rule.other_charges]:
        if treatment == 'SEPARATE_AT_COST':
            exclusions.append(label + ': payable separately at actual cost; not part of this total.')
    total = sum((Decimal(x['amount']) * (-1 if x['kind'] == 'CREDIT' else 1) for x in lines), ZERO).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    if total > Decimal('9999999999.99'):
        raise ValueError('The calculated total exceeds the supported booking amount.')
    return {'method': rule.method, 'currency': 'LKR', 'breakdown': lines, 'total': format(total, '.2f'), 'exclusions': exclusions,
            'policy': 'TRAVELLY_LD_2026_10_27', 'included_km': str(included) if included is not None else None,
            'reserved_service_hours': [str(h) for h in reserved_hours]}
