from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import localtime
import jdatetime
from django.db.models import Sum
from salon.models import Appointment

def message_nitif(appointment, dt, mt):
    user = appointment.customer.nickname()
    shop = appointment.shop.name
    start_local = localtime(dt)
    jalali_date = jdatetime.datetime.fromgregorian(datetime=start_local).strftime('%Y/%m/%d')
    local_clock = start_local.strftime('%H:%M')
    if mt == 'co':
        message = f" {user} برای {jalali_date}-{local_clock} نوبت گرفت"
    elif mt=='cc':
        message = f" {user} نوبت خود در تاریخ {jalali_date}-{local_clock} را لغو کرد"
    elif mt=='mo':
        message = f"مدیر {shop} نوبت شما در تاریخ: {jalali_date}-{local_clock} را تایید کرد"     
    elif mt=='mc':
        message = f"مدیر {shop} نوبت شما در تاریخ: {jalali_date}-{local_clock} را لغو کرد"     
    elif mt=='cp':
        message = f"نوبت شما {user}  در تاریخ: {jalali_date}-{local_clock} با موفقیت انجام شد"     
    return message

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
    now = localtime()  # ساعت فعلی با تایم‌زون صحیح
    future_threshold = now + timedelta(minutes=30)  # حداقل نیم‌ساعت بعد از اکنون
    current_time = work_start
    slot_interval = timedelta(minutes=30)
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

