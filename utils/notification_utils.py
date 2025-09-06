from django.utils.timezone import localtime
import jdatetime


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

