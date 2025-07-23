from django.db import models
from django.contrib.auth.models import AbstractUser

import uuid
import os

DEFAULT_AVATAR_PATH =  '/media/images/avatars/default.png'

# تابع برای تولید نام رندوم فایل آواتار
def get_random_filename(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('images/avatars/', random_filename)

# account/models.py
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'مدیر'),
        ('barber', 'آرایشگر'),
        ('customer', 'مشتری'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(verbose_name='رایانامه',unique=True,blank=True,null=True)


    property
    def nickname(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'


class BarberProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='barber_profile')
    status = models.BooleanField(default=True, verbose_name='وضعیت')
    shop = models.ForeignKey('salon.Shop', on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.ImageField(upload_to=get_random_filename, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class ManagerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='manager_profile')
    avatar = models.ImageField(upload_to=get_random_filename, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    def get_avatar_url(self):
        """برگرداندن URL آواتار یا آواتار پیش‌فرض"""
        if self.avatar:
            return self.avatar.url
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    

class CustomerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='customer_profile')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"