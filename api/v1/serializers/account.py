#ChatGPT:
from rest_framework import serializers, exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction
from django.core.files.storage import default_storage
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.templatetags.static import static
from django.contrib.auth import get_user_model
import random
import string
import os

from utils.date_utils import j_convert_appoiment
from utils.salon_utils import get_active_shop
from apps.account.models import *
from apps.salon.models import *

User = get_user_model()

# 
class ForceChangePasswordSerializer(serializers.Serializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({
                "password2": "رمزهای عبور یکسان نیستند."
            })

        validate_password(data['password1'])
        return data

#-- Self assign barber:
class SelfAssignBarberSerializer(serializers.Serializer):
    def save(self, user, shop):
        barber = getattr(user, "barber_profile", None)

        # قبلاً اصلاً آرایشگر نبوده
        if not barber:
            return BarberProfile.objects.create(
                user=user,
                shop=shop,
                status_barber=BarberStatus.ACTIVE,
            )

        # آرایشگر فعال آرایشگاه دیگر
        if barber.status_barber == BarberStatus.ACTIVE and barber.shop != shop:
            raise serializers.ValidationError(
                {"code":"ACTICE_BARBER_OTHER_SHOP"}
            )

        # آرایشگر همین سالن است ولی فعال نیست → فعالش کن
        if barber.shop == shop and barber.status_barber != BarberStatus.ACTIVE:
            barber.status_barber = BarberStatus.ACTIVE
            barber.save(update_fields=["status_barber"])
            return barber

        # آرایشگر فعال همین سالن است
        if barber.shop == shop and barber.status_barber == BarberStatus.ACTIVE:
            raise serializers.ValidationError(
                {"code":"ACTIVE_BARBER_THIS_SHOP"}
            )

        # حالت LEFT → اتصال مجدد
        barber.shop = shop
        barber.status_barber = BarberStatus.ACTIVE
        barber.save()

        return barber
    
#-- Left managet from barber
class LeaveBarberSerializer(serializers.Serializer):
    def save(self, barber):
        barber.shop = None
        barber.status_barber = BarberStatus.LEFT
        barber.save(update_fields=["shop", "status_barber"])
        return barber

#-- Invite barber by manager:
class InviteBarberSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    force = serializers.BooleanField(required=False, default=False)  # ⬅️ اضافه شد: کنترل دعوت مجدد با تأیید

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError({"code":"INCORRECT_PHONE"})
        return value

    def create_temp_password(self):
        return "".join(random.choices(string.digits, k=6))

    def save(self):
        phone = self.validated_data["phone"]
        force = self.validated_data["force"]  # ⬅️ اضافه شد
        shop = self.context["shop"]

        temp_password = self.create_temp_password()

        user, created = User.objects.get_or_create(
            username=phone,
            defaults={
                "phone": phone,
                "role": "barber",
                "must_change_password": True,
            },
        )
        # New User:
        if created:
            user.set_password(temp_password)
            user.save()

            BarberProfile.objects.create(
                user=user,
                shop=shop,
                invited_at=timezone.now(),
                status_barber=BarberStatus.INVITED,
            )

            print(f"*** Temp password for barber {phone}: {temp_password} ***")
            return user

        # Already User:

        if user.role != "barber":
            raise serializers.ValidationError({"code": "USER_NOT_BARBER"})

        barber = getattr(user, "barber_profile", None)
        if not barber:
            raise serializers.ValidationError({"code": "BARBER_PROFILE_MISSING"})

        if barber.status_barber in [BarberStatus.ACTIVE, BarberStatus.SUSPENDED]:
            raise serializers.ValidationError({"code": "BARBER_ACTIVE"})

        if barber.status_barber == BarberStatus.INVITED:
            if barber.shop != shop:
                raise serializers.ValidationError(
                    {"code": "BARBER_INVITED_OTHER_SHOP"}
                )

            if not force:
                raise serializers.ValidationError(
                    {"code": "BARBER_ALREADY_INVITED"}
                )

            user.set_password(temp_password)
            user.must_change_password = True
            user.save()
            barber.services.update(is_active=True)
            barber.invited_at = timezone.now() 
            barber.save()

            print(f"*** Re-invite barber {phone}: {temp_password} ***")
            return user

        if barber.status_barber == BarberStatus.LEFT:
            user.set_password(temp_password)
            user.must_change_password = True
            user.save()
            barber.services.update(is_active=True)
            barber.shop = shop
            barber.invited_at = timezone.now()
            barber.status_barber = BarberStatus.INVITED
            barber.save()

            print(f"*** Re-invite LEFT barber {phone}: {temp_password} ***")
            return user

        raise serializers.ValidationError({"code": "UNKNOWN_ERROR"})

#-- Remove barber by manager:
class RemoveBarberFromShopSerializer(serializers.Serializer):
    def save(self, barber):
        barber.services.update(is_active=False)
        barber.shop = None
        barber.status_barber = BarberStatus.LEFT
        barber.save(update_fields=["shop", "status_barber"])
        return barber

#-- SignUp OTP Manager & Customer:
class PhoneSerializer(serializers.Serializer):
    phone = serializers.RegexField(
        regex=r'^\d{10,15}$',
        error_messages={'invalid': 'شماره تلفن معتبر نیست.'}
    )

class OTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6)


class BaseSignupSerializer(serializers.Serializer):
    """
    این کلاس برای هر دو نقش مشترک استفاده میشه
    نقش (role) از context گرفته میشه
    """
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField(required=False)
    password1 = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        if value and CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return value

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password2": "گذرواژه‌ها مطابقت ندارند"})
        
        try:
            validate_password(data['password1'])
        except ValidationError as e:
            raise serializers.ValidationError({"password1": list(e.messages)})
        
        return data

    def create(self, validated_data):
        role = self.context.get('role')
        phone = self.context.get('phone')
        if not phone or not role:
            raise exceptions.PermissionDenied("فرآیند ثبت‌نام معتبر نیست")

        user = CustomUser.objects.create_user(
            username=phone,
            phone=phone,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data.get('email', ''),
            password=validated_data['password1'],
            role=role
        )

        if role == 'manager':
            ManagerProfile.objects.create(user=user)
        elif role == 'customer':
            CustomerProfile.objects.create(user=user)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # می‌تونی اطلاعات اضافی رو داخل خود توکن ذخیره کنی
        token['role'] = user.role
        token['must_change_password'] = user.must_change_password
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # اطلاعات اضافی در خروجی لاگین
        data.update({
            'id': self.user.id,
            'username': self.user.username,
            'role': self.user.role,
            'must_change_password': self.user.must_change_password
        })
        return data


# class IsProfileManagerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ["id", "username", "role", "must_change_password"]


class IsProfileManagerSerializer(serializers.ModelSerializer):
    active_shop_id = serializers.SerializerMethodField()
    barber_status = serializers.SerializerMethodField()
    barber_shop_id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "role",
            "must_change_password",
            "active_shop_id",
            "barber_status",
            "barber_shop_id",
        ]

    def get_active_shop_id(self, obj):
        shop = get_active_shop(obj)
        return shop.id if shop else None

    def get_barber_status(self, obj):
        barber = getattr(obj, "barber_profile", None)
        return barber.status_barber if barber else None

    def get_barber_shop_id(self, obj):
        barber = getattr(obj, "barber_profile", None)
        return barber.shop_id if barber and barber.shop else None


# Manager-------------------
class ShopSerializer(serializers.ModelSerializer):
    manage_url = serializers.SerializerMethodField()
    appointments_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ['id', 'name', 'referral_code', 'manage_url', 'appointments_url']

    def get_manage_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.get_manage_url())

    def get_appointments_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.get_appointments_url())

# for web
class ManagerProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    default_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ManagerProfile
        fields = ['id', 'avatar_url', 'bio', 'default_avatar']

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if obj.avatar else None

    def get_default_avatar(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(static("images/default_avatar.png"))

# for web
class ManagerFullProfileSerializer(serializers.Serializer):
    # اطلاعات کاربر
    id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    phone = serializers.CharField(source="user.phone")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")
    nickname = serializers.CharField(source="user.nickname")
    role = serializers.CharField(source="user.role")
    role_display = serializers.CharField(source="user.get_role_display")
    must_change_password = serializers.BooleanField(source="user.must_change_password")

    # پروفایل
    profile = ManagerProfileSerializer(source="manager_profile")

    # فروشگاه‌ها
    shops = ShopSerializer(many=True)

    # لینک ساخت فروشگاه
    create_shop_url = serializers.SerializerMethodField()

    def get_create_shop_url(self, obj):
        request = self.context.get("request")
        from django.urls import reverse
        return request.build_absolute_uri(reverse("salon:create_shop"))

# for mobile
class ManagerProfileApiSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = ManagerProfile
        fields = ['id', 'avatar_url', 'bio']

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None

# for mobile
class ManagerFullProfileApiSerializer(serializers.Serializer):
    # اطلاعات کاربر
    id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    phone = serializers.CharField(source="user.phone")
    email = serializers.EmailField(source="user.email")
    nickname = serializers.CharField(source="user.nickname")
    first_name = serializers.CharField(source="user.first_name",required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name",required=False, allow_blank=True)
    role_display = serializers.CharField(source="user.get_role_display")
    shops = serializers.IntegerField()
    # پروفایل
    profile = ManagerProfileApiSerializer(source="manager_profile")
    jcreated_date = serializers.SerializerMethodField()

    def get_jcreated_date(self, obj):
        user = obj.get("user")
        if not user or not hasattr(user, "date_joined"):
            return None
        return j_convert_appoiment(user.date_joined)

# for mobile
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "تکرار گذرواژه با گذرواژه جدید مطابقت ندارد."})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("گذرواژه فعلی اشتباه است.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


# for web
class ManagerProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, label='نام کاربری')
    phone = serializers.RegexField(
        source='user.phone',
        regex=r'^\d{10,15}$',
        error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},
        label='شماره همراه'
    )
    first_name = serializers.CharField(source='user.first_name', max_length=30, label='نام')
    last_name = serializers.CharField(source='user.last_name', max_length=150, label='نام خانوادگی')
    email = serializers.EmailField(source='user.email', label='ایمیل')
    avatar = serializers.ImageField(
        required=False,
        allow_null=True,
        label='آواتار',
        help_text='فرمت‌های مجاز: JPG، PNG. حداکثر حجم: 5 مگابایت'
    )

    class Meta:
        model = ManagerProfile
        fields = [
            'username', 'phone', 'first_name', 'last_name',
            'email', 'avatar', 'bio'
        ]

    def validate_user__email(self, value):
        """بررسی یکتا بودن ایمیل"""
        user = self.instance.user
        if CustomUser.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return value

    def validate_avatar(self, value):
        if value:
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError('حجم فایل باید کمتر از 5 مگابایت باشد.')
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg']:
                raise serializers.ValidationError('فقط فرمت‌های PNG و JPG مجاز هستند.')
        return value

    def update(self, instance, validated_data):
        # جدا کردن داده‌های کاربر و پروفایل
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
# barber profile:
class BarberProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    phone = serializers.CharField(source='user.phone')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')

    class Meta:
        model = BarberProfile
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'avatar', 'bio']

# barber edit profile: 
class BarberEditProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    phone = serializers.CharField(source='user.phone')
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = BarberProfile
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'avatar',
            'bio',
        ]

    def update(self, instance, validated_data):
        # جدا کردن داده‌های مربوط به User
        user_data = validated_data.pop('user', {})

        # آپدیت فیلدهای user
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        # حذف آواتار قبلی اگر آواتار جدید فرستاده شده باشد
        if 'avatar' in validated_data and validated_data['avatar'] is not None:
            if instance.avatar:
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, instance.avatar.name)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")

        # آپدیت فیلدهای BarberProfile
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

#-- customer profile:
class CustomerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    phone = serializers.CharField(source='user.phone')
    first_name = serializers.CharField(source='user.first_name', allow_blank=True, required=False)
    last_name = serializers.CharField(source='user.last_name', allow_blank=True, required=False)
    email = serializers.EmailField(source='user.email', allow_blank=True, required=False)

    class Meta:
        model = CustomerProfile
        fields = [
            'username',
            'phone',
            'first_name',
            'last_name',
            'email',
            # اگر فیلد اختصاصی CustomerProfile دارید اینجا اضافه کنید
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

#-- CustomerListAPIView:
class CustomerShopSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='customer.username', read_only=True)
    firstname = serializers.CharField(source='customer.first_name', read_only=True)
    lastname = serializers.CharField(source='customer.last_name', read_only=True)
    phone = serializers.CharField(source='customer.phone', read_only=True)

    class Meta:
        model = CustomerShop
        fields = ['customer_id', 'username', 'phone', 'firstname','lastname','is_active', 'joined_at']
