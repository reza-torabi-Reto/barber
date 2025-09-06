from django import template
from utils.date_utils import j_convert_list_appoiment

register = template.Library()

@register.filter(name='j_date')
def j_date(date):
    return j_convert_list_appoiment(date)

@register.filter(name='j_time')
def j_time(time):
    return j_convert_list_appoiment(time, time_only=True)

@register.filter(name='get_services')
def get_services(appointment):
    return ", ".join([service.service.name for service in appointment.selected_services.all()])

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key, [])


import jdatetime
@register.filter
def make_calendar_weeks(day_list):
    """
    لیست روزهای موجود رو به هفته‌هایی تبدیل می‌کنه برای نمایش در قالب تقویم
    """
    # تبدیل لیست تاریخ‌های موجود به یک مجموعه برای دسترسی سریع
    date_map = {d['jalali_date']: d for d in day_list}
    if not day_list:
        return []

    # اولین تاریخ موجود (برای تعیین شروع ماه)
    first = day_list[0]
    first_jdate = jdatetime.date.fromgregorian(date=first['gregorian_date'])

    year, month = first_jdate.year, first_jdate.month
    num_days = jdatetime.j_days_in_month[month - 1]

    weeks = []
    week = [None] * 7

    for day in range(1, num_days + 1):
        jdate = jdatetime.date(year, month, day)
        weekday_index = jdate.weekday()  # 0=شنبه, 6=جمعه
        jalali_str = f"{day} {jdate.j_months_fa[month - 1]} {year}"
        day_of_week = jdate.strftime('%A')

        day_data = date_map.get(jalali_str, {
            'gregorian_date': jdate.togregorian(),
            'jalali_date': jalali_str,
            'day_of_week': day_of_week,
        })

        week[weekday_index] = day_data

        if weekday_index == 6:
            weeks.append(week)
            week = [None] * 7

    if any(week):
        weeks.append(week)

    return weeks
