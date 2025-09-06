# services/appointment.py
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import localtime

from utils.salon_utils import is_slot_available

from apps.salon.models import Appointment


def find_available_time_slots(date, schedule, barber, total_duration): # date=today, schedule=working-days
    work_start = timezone.make_aware(datetime.combine(date, schedule.start_time))
    work_end = timezone.make_aware(datetime.combine(date, schedule.end_time))
    break_start = timezone.make_aware(datetime.combine(date, schedule.break_start)) if schedule.break_start else None
    break_end = timezone.make_aware(datetime.combine(date, schedule.break_end)) if schedule.break_end else None

    booked_slots = Appointment.objects.filter(
        barber=barber,
        start_time__date=date,
        status__in=['pending', 'confirmed']
    ).values('start_time', 'end_time')

    available_slots = []
    now = localtime()  # ساعت فعلی با تایم‌زون صحیح
    future_threshold = now + timedelta(minutes=30)  # حداقل نیم‌ساعت بعد از اکنون
    current_time = work_start
    slot_interval = timedelta(minutes=30)
    while current_time + timedelta(minutes=total_duration) <= work_end:
        slot_end = current_time + timedelta(minutes=total_duration)

        if date == now.date() and current_time < future_threshold:
                   current_time += slot_interval
                   continue

        if is_slot_available(current_time, slot_end, booked_slots, break_start, break_end):
            available_slots.append({
                'start_time': current_time.strftime('%H:%M'),
                'end_time': slot_end.strftime('%H:%M')
            })
        current_time += slot_interval

    return available_slots 

