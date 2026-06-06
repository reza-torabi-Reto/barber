# ./apps/salon/models.py:
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, UniqueConstraint
from django.urls import reverse
from django.utils import timezone
from datetime import  timedelta

import uuid
import os

from utils.generators import generate_referral_code


def get_random_logo_name(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('images/logo_shop/', random_filename)


def get_random_image_shop_name(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('images/image_shop/', random_filename)

class Province(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class City(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('province', 'name')

    def __str__(self):
        return f"{self.name} - {self.province.name}"


class District(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('city', 'name')

    def __str__(self):
        return f"{self.name} - {self.city.name}"


class Shop(models.Model):
    STATUS_CHOISE = (
        ('open', 'باز'),
        ('close', 'بسته'),
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
    )
    
    manager = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='managed_shops', verbose_name="مدیر مسئول")
    name = models.CharField(max_length=100, verbose_name="نام آرایشگاه")
    referral_code = models.CharField(max_length=8, unique=True, verbose_name="کد یکتای جستجو")
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField(verbose_name="آدرس دقیق")
    
    phone = models.CharField(max_length=15, verbose_name="شماره تماس")
    status = models.CharField(max_length=10, choices=STATUS_CHOISE, default='active', verbose_name="وضعیت")
    active = models.BooleanField(default=False, verbose_name="فعال؟")
    create_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    logo = models.ImageField(upload_to=get_random_logo_name, blank=True, null=True)    
    image_shop = models.ImageField(upload_to=get_random_image_shop_name, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.referral_code})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    def get_manage_url(self):
        return reverse("salon:manage_shop", args=[self.id])

    def get_appointments_url(self):
        return reverse("salon:manager_appointments", args=[self.id])
    
    def get_full_address(self):
        """آدرس کامل را برمی‌گرداند"""
        parts = []
        if self.province:
            parts.append(self.province.name)
        if self.city:
            parts.append(self.city.name)
        if self.district:
            parts.append(self.district.name)
        if self.address:
            parts.append(self.address)
        return "، ".join(parts)
    
    class Meta:
        verbose_name = "آرایشگاه"
        verbose_name_plural = "آرایشگاه‌ها"



class Service(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='services', verbose_name="آرایشگاه")
    barber = models.ForeignKey('account.BarberProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='services', verbose_name="آرایشگر")
    name = models.CharField(max_length=100, verbose_name="نام خدمت")
    duration = models.PositiveIntegerField(verbose_name="مدت زمان (دقیقه)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت (تومان)")
    is_active = models.BooleanField(default=True, verbose_name="غعال؟")


    def __str__(self):
        return f"{self.name} - {self.shop.name}"

    class Meta:
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"

class CustomerShop(models.Model):
    customer = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='shop_memberships', verbose_name="مشتری")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customer_memberships', verbose_name="آرایشگاه")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")
    is_active = models.BooleanField(default=True)
    class Meta:
        unique_together = ('customer', 'shop')
        verbose_name = "عضویت مشتری"
        verbose_name_plural = "عضویت‌های مشتریان"

    def __str__(self):
        return f"{self.customer.username} در {self.shop.name}"


# class AppointmentStatus(models.TextChoices):
#     PENDING = "pending", "بی‌پاسخ"
#     CONFIRMED = "confirmed", "پذیرفته‌شده"
#     CANCELED = "canceled", "لغو شده"
#     COMPLETED = "completed", "انجام شده"
#     MISSED = "missed", "انجام نشده"

# class Appointment(models.Model):
    
#     customer = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='appointments')
#     shop = models.ForeignKey('Shop', on_delete=models.CASCADE, related_name='appointments')
#     barber = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='barber_appointments')
#     start_time = models.DateTimeField()
#     end_time = models.DateTimeField()
#     status = models.CharField(max_length=20,choices=AppointmentStatus.choices,default=AppointmentStatus.PENDING)
#     canceled_by = models.CharField(max_length=10,choices=[('customer', 'مشتری'),('manager', 'مدیر'),],null=True, blank=True,verbose_name='لغوکننده')
#     created_at = models.DateTimeField(auto_now_add=True)

#     canceled_by_user = models.ForeignKey('account.CustomUser',null=True,blank=True,on_delete=models.SET_NULL,related_name='canceled_appointments')
#     status_updated_by = models.ForeignKey('account.CustomUser',null=True,blank=True,on_delete=models.SET_NULL,related_name='status_updates')
#     status_updated_at = models.DateTimeField(null=True, blank=True)
    
#     class Meta:
#         constraints = [
#             UniqueConstraint(
#                 fields=['barber', 'start_time'],
#                 condition=~Q(status='canceled'),
#                 name='unique_barber_start_time_active'
#             )
#         ]


#     @property
#     def is_expired(self):
#         if self.status not in ['pending', 'confirmed']:
#             return False

#         now = timezone.localtime()

#         if self.start_time < now:
#             return True

#         return False

#     def get_allowed_transitions(self):

#         if self.status == AppointmentStatus.PENDING:
#             if self.is_expired:
#                 return [
#                     AppointmentStatus.COMPLETED,
#                     AppointmentStatus.MISSED
#                 ]
#             return [
#                 AppointmentStatus.CONFIRMED,
#                 AppointmentStatus.CANCELED
#             ]

#         if self.status == AppointmentStatus.CONFIRMED:
#             if self.is_expired:
#                 return [
#                     AppointmentStatus.COMPLETED,
#                     AppointmentStatus.MISSED
#                 ]
#             return [AppointmentStatus.CANCELED]

#         return []

#     def can_transition_to(self, new_status):
#         return new_status in self.get_allowed_transitions()

#     def transition_to(self, new_status, *, canceled_by=None): #خطا ازین بخشه
#         if not self.can_transition_to(new_status):
#             raise ValidationError(
#                 f"Cannot transition from {self.status} to {new_status}"
#             )

#         if new_status == AppointmentStatus.CANCELED:
#             self.canceled_by = canceled_by

#         self.status = new_status
#         self.save(update_fields=["status", "canceled_by"])

#     def can_cancel(self):
#         if self.status not in [
#             AppointmentStatus.PENDING,
#             AppointmentStatus.CONFIRMED
#         ]:
#             return False
    
#         now = timezone.localtime()
#         cancel_deadline = self.start_time - timedelta(hours=1)
    
#         return now < cancel_deadline

#     def __str__(self):
#         return f"{self.customer.username} - Appointment with {self.barber.username} at {self.start_time}"    


class AppointmentStatus(models.TextChoices):
    PENDING = "pending", "بی‌پاسخ"
    CONFIRMED = "confirmed", "پذیرفته‌شده"
    CANCELED = "canceled", "لغو شده"
    COMPLETED = "completed", "انجام شده"
    MISSED = "missed", "انجام نشده"


class Appointment(models.Model):

    customer = models.ForeignKey( 'account.CustomUser', on_delete=models.CASCADE, related_name='appointments')
    shop = models.ForeignKey('Shop',on_delete=models.CASCADE,related_name='appointments')
    barber = models.ForeignKey('account.CustomUser',on_delete=models.CASCADE,related_name='barber_appointments')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20,choices=AppointmentStatus.choices,default=AppointmentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    canceled_by_user = models.ForeignKey('account.CustomUser',null=True,blank=True,on_delete=models.SET_NULL,related_name='canceled_appointments')
    status_updated_by = models.ForeignKey('account.CustomUser',null=True,blank=True,on_delete=models.SET_NULL,related_name='status_updates')
    status_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['barber', 'start_time'],
                condition=~Q(status='canceled'),
                name='unique_barber_start_time_active'
            )
        ]

    # -----------------------------
    # TIME STATE
    # -----------------------------

    @property
    def is_past(self):
        return self.start_time < timezone.localtime()

    # -----------------------------
    # ROLE-BASED TRANSITIONS
    # -----------------------------

    def get_allowed_transitions(self, actor):

        if actor.role == "customer":

            if actor != self.customer:
                return []

            if self.status in [
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED
            ] and self.can_cancel():
                return [AppointmentStatus.CANCELED]

            return []

        if actor.role == "manager":

            if self.status == AppointmentStatus.PENDING:
                if self.is_past:
                    return [AppointmentStatus.MISSED]
                return [
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.CANCELED
                ]

            if self.status == AppointmentStatus.CONFIRMED:
                if self.is_past:
                    return [
                        AppointmentStatus.COMPLETED,
                        AppointmentStatus.MISSED
                    ]
                else:
                    if self.can_cancel():
                        return [AppointmentStatus.CANCELED]

            return []

        if actor.role == "barber":

            if actor != self.barber:
                return []

            if (
                self.status == AppointmentStatus.CONFIRMED
                and self.is_past
            ):
                return [
                    AppointmentStatus.COMPLETED,
                    AppointmentStatus.MISSED
                ]

            return []

        return []

    # -----------------------------
    # TRANSITION LOGIC
    # -----------------------------

    def transition_to(self, new_status, *, actor):

        allowed = self.get_allowed_transitions(actor)
        print(f'Allow: {allowed}')
        if new_status not in allowed:
            raise ValidationError(
                f"Transition from {self.status} to {new_status} not allowed for {actor.role}"
            )

        self.status = new_status
        self.status_updated_by = actor
        self.status_updated_at = timezone.now()

        if new_status == AppointmentStatus.CANCELED:
            self.canceled_by_user = actor

        self.save(
            update_fields=[
                "status",
                "status_updated_by",
                "status_updated_at",
                "canceled_by_user"
            ]
        )

    # -----------------------------
    # CANCEL RULE
    # -----------------------------

    def can_cancel(self):

        if self.status not in [
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED
        ]:
            return False

        cancel_deadline = self.start_time - timedelta(hours=1)

        return timezone.localtime() < cancel_deadline

    def __str__(self):
        return (
            f"{self.customer.username} - "
            f"{self.barber.username} - "
            f"{self.start_time}"
        )


class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='selected_services', verbose_name="نوبت")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="خدمت انتخابی")
    # quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        verbose_name = "خدمت نوبت"
        verbose_name_plural = "خدمات نوبت‌ها"

    def __str__(self):
        return f"{self.appointment.id} - {self.service.name}"
    
# بی استفاده(؟)
class ShopSchedule(models.Model):
    DAY_CHOICES = (
        ('saturday', 'شنبه'),
        ('sunday', 'یک‌شنبه'),
        ('monday', 'دوشنبه'),
        ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'),
        ('thursday', 'پنج‌شنبه'),
        ('friday', 'جمعه'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_open = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('shop', 'day_of_week')

    def clean(self):
        if self.is_open:
            if not self.start_time or not self.end_time:
                raise ValidationError("Start time and end time are required if the shop is open.")
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")
            if self.break_start and self.break_end:
                if self.break_start >= self.break_end:
                    raise ValidationError("Break end time must be after break start time.")
                if self.break_start < self.start_time or self.break_end > self.end_time:
                    raise ValidationError("Break time must be within working hours.")
            elif (self.break_start and not self.break_end) or (self.break_end and not self.break_start):
                raise ValidationError("Both break start and break end times must be provided, or neither.")
        else:
            self.start_time = None
            self.end_time = None
            self.break_start = None
            self.break_end = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.shop.name} - {self.get_day_of_week_display()}"



class BarberSchedule(models.Model):
    DAY_CHOICES = (
        ('saturday', 'شنبه'),
        ('sunday', 'یک‌شنبه'),
        ('monday', 'دوشنبه'),
        ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'),
        ('thursday', 'پنج‌شنبه'),
        ('friday', 'جمعه'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='schedule')
    barber = models.ForeignKey('account.BarberProfile', on_delete=models.CASCADE, related_name='schedules_barber')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_open = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('shop', 'barber', 'day_of_week')  

    def clean(self):
        if self.is_open:
            if not self.start_time or not self.end_time:
                raise ValidationError("Start time and end time are required if the shop is open.")
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")
            if self.break_start and self.break_end:
                if self.break_start >= self.break_end:
                    raise ValidationError("Break end time must be after break start time.")
                if self.break_start < self.start_time or self.break_end > self.end_time:
                    raise ValidationError("Break time must be within working hours.")
            elif (self.break_start and not self.break_end) or (self.break_end and not self.break_start):
                raise ValidationError("Both break start and break end times must be provided, or neither.")
        else:
            self.start_time = None
            self.end_time = None
            self.break_start = None
            self.break_end = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.shop.name} - {self.get_day_of_week_display()}"



from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    user = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='notifications')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(null=True, blank=True)

    # مثلا نوع نوتیفیکیشن (اختیاری)
    type = models.CharField(max_length=50, choices=(
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('appointment_canceled', 'Appointment Canceled'),
        ('other', 'Other'),
    ), default='other')
    
    def __str__(self):
        return f'Notification for {self.user} - Read: {self.is_read}'
