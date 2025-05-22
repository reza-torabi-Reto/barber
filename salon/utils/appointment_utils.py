from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import make_aware, localtime

from django.db.models import Sum
from salon.models import Appointment

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
    # now = timezone.now()
    now = localtime()  # ساعت فعلی با تایم‌زون صحیح
    future_threshold = now + timedelta(minutes=30)  # حداقل نیم‌ساعت بعد از اکنون
    # print(f'now: {now}, future_threshold: {future_threshold}')
    # print("++++++++++++++++")
    current_time = work_start
    slot_interval = timedelta(minutes=30)
    # print(f"current_time: {current_time}")
    # print("++++++++++++++++")
    while current_time + timedelta(minutes=total_duration) <= work_end:
        slot_end = current_time + timedelta(minutes=total_duration)

        if date == now.date() and current_time < future_threshold:
                   current_time += slot_interval
                   print(f"date: {date}, current_time: {current_time}, slot_interval: {slot_interval}")
                   print("////////////////////////")
                   continue

        if is_slot_available(current_time, slot_end, booked_slots, break_start, break_end):
            available_slots.append({
                'start_time': current_time.strftime('%H:%M'),
                'end_time': slot_end.strftime('%H:%M')
            })
        current_time += slot_interval

    return available_slots 
    """ 
            output -> [
                    {"start_time": "14:00", "end_time": "14:30"},
                    {"start_time": "14:30", "end_time": "15:00"},
                    ...
                ]"""
