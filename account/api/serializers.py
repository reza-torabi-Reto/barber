# account/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from account.models import CustomUser, ManagerProfile,ManagerProfile, CustomUser
from salon.models import Shop

# Serializer برای پروفایل مدیر
class ManagerProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = ManagerProfile
        fields = ['avatar_url', 'bio']

    def get_avatar_url(self, obj):
        return obj.get_avatar_url() if obj.avatar else None

# Serializer برای کاربر
class ManagerUserSerializer(serializers.ModelSerializer):
    manager_profile = ManagerProfileSerializer()

    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'nickname', 'manager_profile']

# Serializer برای آرایشگاه‌ها
class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'referral_code']


# Register Manager
class ManagerSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    avatar = serializers.ImageField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'phone', 'password', 'password2', 'avatar', 'bio']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': "رمز عبور با تکرار آن مطابقت ندارد."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password2')
        avatar = validated_data.pop('avatar', None)
        bio = validated_data.pop('bio', '')

        user = CustomUser.objects.create(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            role='manager'
        )
        user.set_password(password)
        user.save()

        ManagerProfile.objects.create(user=user, avatar=avatar, bio=bio)
        return user


#Edit Profile Manager
class ManagerProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email', allow_blank=True, allow_null=True)
    address = serializers.CharField(source='user.address', allow_blank=True, allow_null=True)

    class Meta:
        model = ManagerProfile
        fields = ['avatar', 'bio', 'first_name', 'last_name', 'email', 'address']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})

        # به‌روزرسانی فیلدهای یوزر
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # به‌روزرسانی پروفایل
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        data['role'] = user.role
        
        # مشخص کردن URL مقصد بر اساس نقش
        if user.role == 'manager':
            data['redirect_url'] = '/manager/profile/'
        elif user.role == 'customer':
            data['redirect_url'] = '/customer/profile/'
        elif user.role == 'barber':
            data['redirect_url'] = '/barber/profile/'
        else:
            data['redirect_url'] = '/home/'

        return data
