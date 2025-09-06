from django.db.models import Sum


def get_total_service_duration(services):
    return services.aggregate(total=Sum('duration'))['total'] or 0


def is_slot_available(current_time, slot_end, booked_slots, break_start=None, break_end=None):
    if break_start and break_end:
        if break_start <= current_time < break_end or break_start < slot_end <= break_end:
            return False
    for slot in booked_slots:
        booked_start = slot['start_time']
        booked_end = slot['end_time']
        if not (slot_end <= booked_start or current_time >= booked_end):
            return False
    return True
