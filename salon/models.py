# salon/models.py
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.db.models import Q, UniqueConstraint
from .utils.generate_referral import generate_referral_code

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
    address = models.TextField(verbose_name="آدرس دقیق")
    phone = models.CharField(max_length=15, verbose_name="شماره تماس")
    status = models.CharField(max_length=10, choices=STATUS_CHOISE, default='active', verbose_name="وضعیت")
    create_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    # latitude = models.FloatField(null=True, blank=True, verbose_name="عرض جغرافیایی")
    # longitude = models.FloatField(null=True, blank=True, verbose_name="طول جغرافیایی")
    
    def __str__(self):
        return f"{self.name} ({self.referral_code})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "آرایشگاه"
        verbose_name_plural = "آرایشگاه‌ها"
# salon/models.py
class Service(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='services', verbose_name="آرایشگاه")
    barber = models.ForeignKey('account.BarberProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='services', verbose_name="آرایشگر")
    name = models.CharField(max_length=100, verbose_name="نام خدمت")
    duration = models.PositiveIntegerField(verbose_name="مدت زمان (دقیقه)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت (تومان)")

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


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('confirmed', 'تأیید شده'),
        ('canceled', 'لغو شده'),
        ('completed', 'تکمیل شده'),
    )

    customer = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='appointments')
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, related_name='appointments')
    barber = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='barber_appointments')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['barber', 'start_time'],
                condition=~Q(status='canceled'),
                name='unique_barber_start_time_active'
            )
        ]


    def __str__(self):
        return f"{self.customer.username} - Appointment with {self.barber.username} at {self.start_time}"    


class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='selected_services', verbose_name="نوبت")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="خدمت انتخابی")
    # quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        verbose_name = "خدمت نوبت"
        verbose_name_plural = "خدمات نوبت‌ها"

    def __str__(self):
        return f"{self.appointment.id} - {self.service.name}"
    

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
