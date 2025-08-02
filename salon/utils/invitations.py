from account.models import CustomUser, BarberProfile
from django.contrib import messages
import random


def generate_temp_password():
    return str(random.randint(100000, 999999))  # یا ترکیب حروف و اعداد


def invite_or_reinvite_barber(request, shop, phone, first_name='', last_name=''):
    """
    دعوت یا دعوت مجدد یک آرایشگر بر اساس شماره تلفن.

    :param request: شیٔ ریکوئست برای پیام‌ها
    :param shop: شیٔ آرایشگاه
    :param phone: شماره همراه
    :param first_name: در صورت نیاز (کاربر جدید)
    :param last_name: در صورت نیاز (کاربر جدید)
    :return: (status: bool, message: str)
    """

    existing_user = CustomUser.objects.filter(phone=phone).first()

    if existing_user:
        if existing_user.role == 'barber' and existing_user.must_change_password:
            temp_password = generate_temp_password()
            existing_user.set_password(temp_password)
            existing_user.save()
            print(f"رمز موقت جدید برای آرایشگر ارسال شد: {temp_password}")
            messages.success(request, f"رمز موقت جدید برای آرایشگر ارسال شد: {temp_password}")
            return True, "دعوت مجدد انجام شد."

        elif existing_user.role == 'barber' and hasattr(existing_user, 'barber_profile') and existing_user.barber_profile.shop is None:
            existing_user.barber_profile.shop = shop
            existing_user.barber_profile.save()
            messages.success(request, "آرایشگر قبلی به این آرایشگاه اضافه شد.")
            return True, "دعوت مجدد موفق."

        else:
            return False, "کاربری با این شماره قبلاً ثبت‌نام کرده است."

    else:
        temp_password = generate_temp_password()
        user = CustomUser.objects.create_user(
            username=phone,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            password=temp_password,
            role='barber',
            is_active=True,
            must_change_password=True
        )
        BarberProfile.objects.create(user=user, shop=shop)
        print(f"رمز موقت برای آرایشگر ارسال شد: {temp_password}")
        messages.success(request, f"آرایشگر با موفقیت اضافه شد. رمز موقت: {temp_password}")
        return True, "آرایشگر جدید ساخته شد."
