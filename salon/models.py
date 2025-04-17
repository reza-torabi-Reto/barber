# salon/models.py
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from .utils import generate_referral_code

class Shop(models.Model):
    manager = models.ForeignKey('account.UserProfile', on_delete=models.CASCADE, related_name='managed_shops', verbose_name="مدیر مسئول")
    name = models.CharField(max_length=100, verbose_name="نام آرایشگاه")
    referral_code = models.CharField(max_length=8, unique=True, verbose_name="کد یکتای جستجو")
    address = models.TextField(verbose_name="آدرس دقیق")
    phone = models.CharField(max_length=15, verbose_name="شماره تماس")
    status = models.CharField(max_length=10, choices=[('active', 'فعال'), ('inactive', 'غیرفعال')], default='active', verbose_name="وضعیت")
    latitude = models.FloatField(null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(null=True, blank=True, verbose_name="طول جغرافیایی")

    def __str__(self):
        return f"{self.name} ({self.referral_code})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "آرایشگاه"
        verbose_name_plural = "آرایشگاه‌ها"

class Service(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='services', verbose_name="آرایشگاه")
    name = models.CharField(max_length=100, verbose_name="نام خدمت")
    duration = models.PositiveIntegerField(verbose_name="مدت زمان (دقیقه)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت (تومان)")

    def __str__(self):
        return f"{self.name} - {self.shop.name}"

    class Meta:
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"

class CustomerShop(models.Model):
    customer = models.ForeignKey('account.Customer', on_delete=models.CASCADE, related_name='shop_memberships', verbose_name="مشتری")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customer_memberships', verbose_name="آرایشگاه")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")

    class Meta:
        unique_together = ('customer', 'shop')
        verbose_name = "عضویت مشتری"
        verbose_name_plural = "عضویت‌های مشتریان"

    def __str__(self):
        return f"{self.customer.username} در {self.shop.name}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('confirmed', 'تایید شده'),
        ('canceled', 'لغو شده'),
    ]
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='appointments', verbose_name="آرایشگاه")
    barber = models.ForeignKey('account.Barber', on_delete=models.CASCADE, related_name='barber_appointments', verbose_name="آرایشگر")  # تغییر related_name
    customer = models.ForeignKey('account.Customer', on_delete=models.CASCADE, related_name='customer_appointments', verbose_name="مشتری")  # تغییر related_name
    start_time = models.DateTimeField(verbose_name="زمان شروع")
    end_time = models.DateTimeField(verbose_name="زمان پایان")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت نوبت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        unique_together = ('barber', 'start_time')
        verbose_name = "نوبت"
        verbose_name_plural = "نوبت‌ها"

    def __str__(self):
        return f"{self.customer.username} - {self.start_time}"

    def save(self, *args, **kwargs):
        total_duration = self.selected_services.aggregate(Sum('service__duration'))['service__duration__sum'] or 0
        self.end_time = self.start_time + timezone.timedelta(minutes=total_duration)
        super().save(*args, **kwargs)

class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='selected_services', verbose_name="نوبت")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="خدمت انتخابی")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        verbose_name = "خدمت نوبت"
        verbose_name_plural = "خدمات نوبت‌ها"

    def __str__(self):
        return f"{self.appointment.id} - {self.service.name}"