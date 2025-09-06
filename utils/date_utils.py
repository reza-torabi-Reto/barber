import jdatetime
import datetime

PERSIAN_MONTHS = {
    'Farvardin': 'فروردین',
    'Ordibehesht': 'اردیبهشت',
    'Khordad': 'خرداد',
    'Tir': 'تیر',
    'Mordad': 'مرداد',
    'Shahrivar': 'شهریور',
    'Mehr': 'مهر',
    'Aban': 'آبان',
    'Azar': 'آذر',
    'Dey': 'دی',
    'Bahman': 'بهمن',
    'Esfand': 'اسفند',
}

PERSIAN_WEEKDAYS = {
        'Saturday': 'شنبه',
        'Sunday': 'یکشنبه',
        'Monday': 'دوشنبه',
        'Tuesday': 'سه‌شنبه',
        'Wednesday': 'چهارشنبه',
        'Thursday': 'پنج‌شنبه',
        'Friday': 'جمعه',
    }

def j_convert_appoiment(date):
    
    # jalali_date = jdatetime.date.fromgregorian(date=date)
    jalali_date = jdatetime.date.fromgregorian(date=date)#jalali_date.strftime('%d %B %Y')#.replace(' 0', '')  # مثلاً "7 Ordibehesht 1404"
    jalali_date_str = jalali_date.strftime('%d %B %Y')
    for en_month, fa_month in PERSIAN_MONTHS.items():
        jalali_date_str = jalali_date_str.replace(en_month, fa_month)
    
    return jalali_date_str


def j_convert_list_appoiment(date, time_only=False):
    
    if isinstance(date, datetime.datetime):
        jalali_date = jdatetime.datetime.fromgregorian(datetime=date)
        weekday_name = jalali_date.strftime('%A')
        if time_only:
            jalali_date_str = jalali_date.strftime('%H:%M')
        else:
            jalali_date_str = jalali_date.strftime('%d %B %Y')
            for en_month, fa_month in PERSIAN_MONTHS.items():
                jalali_date_str = jalali_date_str.replace(en_month, fa_month)
            weekday_name = PERSIAN_WEEKDAYS.get(weekday_name, weekday_name)  
            jalali_date_str = f"{weekday_name}، {jalali_date_str}"  # اضافه کردن نام روز هفته به تاریخ
    elif isinstance(date, datetime.date):
        jalali_date = jdatetime.date.fromgregorian(date=date)
        jalali_date_str = jalali_date.strftime('%d %B %Y')
        for en_month, fa_month in PERSIAN_MONTHS.items():
            jalali_date_str = jalali_date_str.replace(en_month, fa_month)
    else:
        return date  # اگر نوع ورودی ناشناخته باشد، مقدار اصلی را برگردان

    return jalali_date_str
