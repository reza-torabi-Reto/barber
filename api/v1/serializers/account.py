from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers, exceptions
import random
import string
from utils.date_utils import j_convert_appoiment
from utils.salon_utils import get_active_shop
from apps.account.models import *
from apps.salon.models import *

#========================
# MANAGER ACCOUNT SERIALIZERS
#========================

User = get_user_model()

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

class SelfAssignBarberSerializer(serializers.Serializer): 
    def save(self, user, shop):
        barber = getattr(user, "barber_profile", None)

        if not barber:
            return BarberProfile.objects.create(
                user=user,
                shop=shop,
                status_barber=BarberStatus.ACTIVE,
            )

        if barber.status_barber == BarberStatus.ACTIVE and barber.shop != shop:
            raise serializers.ValidationError(
                {"code":"ACTICE_BARBER_OTHER_SHOP"}
            )

        if barber.shop == shop and barber.status_barber != BarberStatus.ACTIVE:
            barber.status_barber = BarberStatus.ACTIVE
            barber.save(update_fields=["status_barber"])
            return barber

        if barber.shop == shop and barber.status_barber == BarberStatus.ACTIVE:
            raise serializers.ValidationError(
                {"code":"ACTIVE_BARBER_THIS_SHOP"}
            )

        barber.shop = shop
        barber.status_barber = BarberStatus.ACTIVE
        barber.save()

        return barber
    
class LeaveBarberSerializer(serializers.Serializer): 
    def save(self, barber):
        barber.shop = None
        barber.status_barber = BarberStatus.LEFT
        barber.save(update_fields=["shop", "status_barber"])
        return barber

class InviteBarberSerializer(serializers.Serializer): 
    phone = serializers.CharField(max_length=15)
    force = serializers.BooleanField(required=False, default=False)  

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError({"code":"INCORRECT_PHONE"})
        return value

    def create_temp_password(self):
        return "".join(random.choices(string.digits, k=6))

    def save(self):
        phone = self.validated_data["phone"]
        force = self.validated_data["force"]  
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


class RemoveBarberFromShopSerializer(serializers.Serializer): 
    def save(self, barber):
        barber.services.update(is_active=False)
        barber.shop = None
        barber.status_barber = BarberStatus.LEFT
        barber.save(update_fields=["shop", "status_barber"])
        return barber


class PhoneSerializer(serializers.Serializer): 
    phone = serializers.RegexField(regex=r'^\d{10,15}$',error_messages={'invalid': 'شماره تلفن معتبر نیست.'})


class OTPSerializer(serializers.Serializer): 
    otp_code = serializers.CharField(max_length=6, min_length=6)


class BaseSignupSerializer(serializers.Serializer): 
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

class ManagerProfileApiSerializer(serializers.ModelSerializer): 
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = ManagerProfile
        fields = ['id', 'avatar_url', 'bio']

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


class ManagerFullProfileApiSerializer(serializers.Serializer): 
    id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    phone = serializers.CharField(source="user.phone")
    email = serializers.EmailField(source="user.email")
    nickname = serializers.CharField(source="user.nickname")
    first_name = serializers.CharField(source="user.first_name",required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name",required=False, allow_blank=True)
    role_display = serializers.CharField(source="user.get_role_display")
    shops = serializers.IntegerField()

    profile = ManagerProfileApiSerializer(source="manager_profile")
    jcreated_date = serializers.SerializerMethodField()

    def get_jcreated_date(self, obj):
        user = obj.get("user")
        if not user or not hasattr(user, "date_joined"):
            return None
        return j_convert_appoiment(user.date_joined)


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
