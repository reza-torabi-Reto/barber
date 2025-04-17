# account/models.py
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class UserProfile(AbstractUser):
    ROLE_CHOICES = [
        ('manager', 'مدیر'),
        ('barber', 'آرایشگر'),
        ('customer', 'مشتری'),
    ]
    
    username = models.CharField(max_length=150, unique=True, verbose_name="نام کاربری")
    password = models.CharField(max_length=128, verbose_name="رمز عبور")
    nickname = models.CharField(max_length=100, null=True, blank=True, verbose_name="نام مستعار")
    phone = models.CharField(max_length=15, unique=True, verbose_name="شماره تلفن")
    email = models.EmailField(null=True, blank=True, verbose_name="ایمیل")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="نقش")
    status = models.CharField(
        max_length=10,
        choices=[('active', 'فعال'), ('inactive', 'غیرفعال')],
        default='active',
        verbose_name="وضعیت"
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="تصویر پروفایل")
    about = models.TextField(null=True, blank=True, verbose_name="درباره من")
    shop = models.ForeignKey('salon.Shop', on_delete=models.CASCADE, null=True, blank=True, related_name='barbers', verbose_name="آرایشگاه")
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.username

class Manager(UserProfile):
    class Meta:
        proxy = True
        verbose_name = "مدیر"
        verbose_name_plural = "مدیران"

class Barber(UserProfile):
    class Meta:
        proxy = True
        verbose_name = "آرایشگر"
        verbose_name_plural = "آرایشگران"

class Customer(UserProfile):
    class Meta:
        proxy = True
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"