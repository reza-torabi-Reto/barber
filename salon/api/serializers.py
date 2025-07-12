from rest_framework import serializers
from salon.models import Shop, Service
from account.models import CustomUser,BarberProfile


class ShopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'phone']


class BarberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'nickname', 'phone','is_active']
    
    is_active = serializers.BooleanField(source='barber_profile.status')


class ServiceSerializer(serializers.ModelSerializer):
    barber_name = serializers.CharField(source='barber.user.nickname')

    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration', 'barber_name']


class ShopSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display')
    manager_nickname = serializers.CharField(source='manager.nickname')

    class Meta:
        model = Shop
        fields = ['id', 'name', 'status', 'referral_code', 'manager_nickname', 'phone', 'address', 'create_date']


class ShopManageSerializer(serializers.Serializer):
    shop = ShopSerializer()
    barbers = BarberSerializer(many=True)
    services = ServiceSerializer(many=True)
    appointments = serializers.DictField()


class ShopEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone', 'status', 'logo', 'image_shop']
        extra_kwargs = {
            'logo': {'required': False},
            'image_shop': {'required': False},
        }

    def validate_status(self, value):
        if value not in ['open', 'close', 'active', 'inactive']:
            raise serializers.ValidationError("وضعیت نامعتبر است.")
        return value


class BarberCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'phone', 'password']

    def create(self, validated_data):
        shop = self.context.get('shop')
        password = validated_data.pop('password')
        phone = validated_data.pop('phone')

        user = CustomUser(**validated_data)
        user.set_password(password)
        user.role = 'barber'
        user.phone = phone
        user.save()

        BarberProfile.objects.create(user=user, shop=shop, status=True)
        return user


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration', 'barber']

    def validate_barber(self, barber):
        shop = self.context['shop']
        if barber.shop != shop or not barber.status:
            raise serializers.ValidationError("آرایشگر معتبر نیست.")
        return barber
