#ChatGPT:
from rest_framework import serializers, exceptions
from rest_framework import serializers

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.templatetags.static import static
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model

from apps.account.models import CustomUser, ManagerProfile, BarberProfile, CustomerProfile
from apps.salon.models import Shop, CustomerShop
import os

User = get_user_model()


# account/serializers.py

class ForcePasswordChangeSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password1'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password2": "رمز عبور با تکرار آن یکسان نیست."})
        password_validation.validate_password(attrs['new_password1'], self.context['request'].user)
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password1'])
        user.save()
        return user

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

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "role", "must_change_password"]


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
