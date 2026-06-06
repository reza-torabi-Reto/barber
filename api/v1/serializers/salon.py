from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.timezone import localdate
from django.utils import timezone
from rest_framework import serializers
from datetime import  timedelta
from utils.date_utils import j_convert_appoiment  
from apps.account.models import BarberProfile
from apps.salon.models import *

#========================
# MANAGER SALON SERIALIZERS
#========================

class CustomerOfSalonSerializer(serializers.ModelSerializer): 
    id = serializers.IntegerField(source='customer.id')
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='customer.phone')
    first_name = serializers.CharField(source='customer.first_name')
    last_name = serializers.CharField(source='customer.last_name')
    is_active = serializers.BooleanField()
    joined_at = serializers.SerializerMethodField()
    joined_at_gregorian = serializers.DateTimeField(source='joined_at', read_only=True)  
    total_appointments = serializers.SerializerMethodField()  

    class Meta:
        model = CustomerShop
        fields = ['id', 'name','first_name','last_name', 'phone', 'joined_at', 'is_active','joined_at_gregorian','total_appointments']
    
    def get_joined_at(self, obj):
        
        return j_convert_appoiment(obj.joined_at)

    def get_name(self, obj):
        full_name = obj.customer.get_full_name()
        return full_name if full_name else obj.customer.username

    def get_total_appointments(self, obj):
        return Appointment.objects.filter(
        customer=obj.customer,
        shop=obj.shop  
    ).count()

class CustomerProfileDetailSerializer(serializers.Serializer): 
    customer_id = serializers.IntegerField()
    nickname = serializers.CharField()
    phone = serializers.CharField()
    joined_at = serializers.CharField()
    is_active = serializers.BooleanField()

    total_completed = serializers.IntegerField()
    total_canceled = serializers.IntegerField()
    total_pending = serializers.IntegerField()

    latest_pending = serializers.DictField(allow_null=True)

class AppointmentSerializer(serializers.ModelSerializer):
    barber_name = serializers.SerializerMethodField()
    barber_id = serializers.CharField(source='barber.id', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    j_start_date = serializers.SerializerMethodField()
    start_time_str = serializers.SerializerMethodField()
    end_time_str = serializers.SerializerMethodField()
    # is_expired = serializers.BooleanField(read_only=True)
    is_expired = serializers.SerializerMethodField()


    class Meta:
        model = Appointment
        fields = [
            'id',
            'barber_name',
            'barber_id',
            'customer_name',
            'status',
            'start_time',
            'end_time',
            'j_start_date',
            'start_time_str',
            'end_time_str',
            'is_expired'
        ]
    def get_barber_name(self, obj):
        barber_user = obj.barber

        if not barber_user:
            return "آرایشگر حذف‌شده"

        full_name = barber_user.get_full_name() or barber_user.username

        try:
            barber_profile = barber_user.barber_profile
        except BarberProfile.DoesNotExist:
            return full_name

        if barber_profile.shop_id == obj.shop_id and barber_profile.status_barber == "invited" :
            return f"{full_name} (آرایشگر دعوت شده)"

        if barber_profile.shop_id != obj.shop_id:
            return f"{full_name} (آرایشگر سابق)"

        return full_name

    def get_j_start_date(self, obj):
        return j_convert_appoiment(obj.start_time)

    def get_start_time_str(self, obj):
        local_time = timezone.localtime(obj.start_time)
        return local_time.strftime('%H:%M')

    def get_end_time_str(self, obj):
        local_time = timezone.localtime(obj.end_time)
        return local_time.strftime('%H:%M')
    
    def get_is_expired(self, obj):
        if obj.status not in [
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED
        ]:
            return False

        return obj.is_past

    

class AppointmentDetailSerializer(serializers.ModelSerializer): 
    customer_name = serializers.SerializerMethodField()
    barber_name = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    jalali_date = serializers.SerializerMethodField()
    start_time_str = serializers.SerializerMethodField()
    end_time_str = serializers.SerializerMethodField()
    available_transitions = serializers.SerializerMethodField()
    canceled_by_display = serializers.SerializerMethodField()
    # is_expired = serializers.BooleanField(read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    class Meta:
        model = Appointment
        fields = [
            'id',
            'customer_name',
            'barber_name',
            'services',
            'total_price',
            'total_duration',
            'status_display',
            'jalali_date',
            'start_time_str',
            'end_time_str',
            'available_transitions',
            'status',
            'canceled_by_display',
            'is_expired',
            'can_cancel'
        ]
    
    def get_available_transitions(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        return obj.get_allowed_transitions(request.user)


    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_barber_name(self, obj):
        return obj.barber.get_full_name() or obj.barber.username

    def get_services(self, obj):
        services = []
        total_price = 0
        total_duration = 0

        for s in obj.selected_services.all():
            price = int(s.service.price)

            services.append({
                "id": s.service.id,
                "name": s.service.name,
                "price": price,
                "duration": s.service.duration,
            })

            total_price += price
            total_duration += s.service.duration

        self._total_price = total_price
        self._total_duration = total_duration

        return services

    def get_total_price(self, obj):
        return getattr(self, "_total_price", 0)

    def get_total_duration(self, obj):
        return getattr(self, "_total_duration", 0)


    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_start_time_str(self, obj):
        local_time = timezone.localtime(obj.start_time)
        return local_time.strftime('%H:%M')

    def get_end_time_str(self, obj):
        local_time = timezone.localtime(obj.end_time)
        return local_time.strftime('%H:%M')

    def get_jalali_date(self, obj):
        return j_convert_appoiment(obj.start_time)
    
    # def get_canceled_by_display(self, obj):
    #   if obj.status == "canceled" and obj.canceled_by:
    #       return dict(Appointment._meta.get_field("canceled_by").choices).get(obj.canceled_by)
    #   return None
    
    def get_is_expired(self, obj):
        if obj.status not in [
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED
        ]:
            return False

        return obj.is_past

    def get_canceled_by_display(self, obj):
        if obj.status == AppointmentStatus.CANCELED and obj.canceled_by_user:
            return obj.canceled_by_user.get_full_name() or obj.canceled_by_user.username
        return None


    def get_can_cancel(self, obj):
        return obj.can_cancel()


class ShopSummarySerializer(serializers.ModelSerializer): 
    class Meta:
        model = Shop
        fields = [
            'id',
            'name',
            'logo',
        ]

class BarberListSerializer(serializers.ModelSerializer): 
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    role = serializers.CharField(source="user.role")
    avatar = serializers.SerializerMethodField()
    today_count = serializers.SerializerMethodField()

    class Meta:
        model = BarberProfile
        fields = ['id','status_barber', 'role','first_name', 'last_name', 'avatar', 'status', 'today_count']

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_today_count(self, obj):
        today = timezone.localdate()
        return Appointment.objects.filter(
            barber=obj.user,
            start_time__date=today,
            status__in=['pending', 'confirmed']  # فقط نوبت‌های فعال امروز
        ).count()

class BarberListAddServiceSerializer(serializers.ModelSerializer): 
    
    name = serializers.SerializerMethodField()
    class Meta:
        model = BarberProfile
        fields = ['id','status_barber','name',]
    def get_name(self, obj):
        return obj.user.nickname() or obj.user.username


class ServiceListSerializer(serializers.ModelSerializer): 
    barber = serializers.SerializerMethodField()
    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "price",
            "duration",
            "is_active",
            "barber"
        ]
    def get_barber(self, obj):
        if obj.barber:
            return {
                "id": obj.barber.id,
                "first_name": obj.barber.user.first_name,
                "last_name": obj.barber.user.last_name,
            }
        return None

class ServiceCreateUpdateSerializer(serializers.ModelSerializer): 
    barber = serializers.PrimaryKeyRelatedField(
        queryset=BarberProfile.objects.all(),
        write_only=True
    )
    barber_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "price",
            "duration",
            "is_active",
            "barber",          # فقط برای POST / PATCH
            "barber_detail",   # فقط برای response
        ]

    def get_barber_detail(self, obj):
        if obj.barber:
            return {
                "id": obj.barber.id,
                "first_name": obj.barber.user.first_name,
                "last_name": obj.barber.user.last_name,
            }
        return None

class ShopUpdateSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone']
        extra_kwargs = {
            'name': {'required': False},
            'address': {'required': False},
            'phone': {'required': False},
        }

class ShopLogoUpdateSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Shop
        fields = ['logo']
        extra_kwargs = {
            'logo': {'required': True},
        }
class ShopImageSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Shop
        fields = ['image_shop']

class ShopDetailSerializer(serializers.ModelSerializer): 
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ['name', 'phone', 'address','full_address', 'logo', 'image_shop','referral_code']
    def get_full_address(self, obj):
        return obj.get_full_address()


class BarberDailyScheduleSerializer(serializers.ModelSerializer): 
    label = serializers.SerializerMethodField()

    class Meta:
        model = BarberSchedule
        fields = [
            "day_of_week", "label",
            "is_open",
            "start_time", "end_time",
            "break_start", "break_end"
        ]

    def get_label(self, obj):
        return dict(BarberSchedule.DAY_CHOICES).get(obj.day_of_week)

class BarberFullScheduleSerializer(serializers.Serializer): 
    schedule = serializers.ListField()

    def update(self, instance, validated_data):
        schedule_data = validated_data.get("schedule", [])

        errors = []

        for item in schedule_data:
            day = item["day_of_week"]
            schedule_obj = instance.schedules_barber.get(day_of_week=day)

            schedule_obj.is_open = item["is_open"]

            if item["is_open"]:
                schedule_obj.start_time = item["start_time"]
                schedule_obj.end_time = item["end_time"]
                schedule_obj.break_start = item.get("break_start")
                schedule_obj.break_end = item.get("break_end")
            else:
                schedule_obj.start_time = None
                schedule_obj.end_time = None
                schedule_obj.break_start = None
                schedule_obj.break_end = None

            try:
                schedule_obj.clean()
                schedule_obj.save()
            except DjangoValidationError as e:
                errors.append({day: e.messages})

        if errors:
            raise serializers.ValidationError({"errors": errors})

        return instance
    
class BarberAppointmentStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    canceled = serializers.IntegerField()
    pending = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    today_count = serializers.IntegerField()


class BarberProfileDetailSerializer(serializers.ModelSerializer): 
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    phone = serializers.CharField(source="user.phone")
    email = serializers.CharField(source="user.email")
    date_joined_jalali = serializers.SerializerMethodField()
    appointments_stats = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = BarberProfile
        fields = [
            "id",
            "status_barber",
            "avatar",
            "bio",
            "shop",
            "first_name",
            "last_name",
            "phone",
            "email",
            "date_joined_jalali",
            "appointments_stats",
        ]

    def get_date_joined_jalali(self, obj):
        return j_convert_appoiment(obj.user.date_joined)

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_appointments_stats(self, obj):
        today = localdate()
        qs = Appointment.objects.filter(barber=obj.user)

        data = {
            "total": qs.count(),
            "completed": qs.filter(status="completed").count(),
            "canceled": qs.filter(status="canceled").count(),
            "pending": qs.filter(status="pending").count(),
            "confirmed": qs.filter(status="confirmed").count(),
            "today_count": qs.filter(start_time__date=today).count(),
        }

        return BarberAppointmentStatsSerializer(data).data

# get list provinces:
class ProvinceSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Province
        fields = ["id", "name"]

# get list cities:
class CitySerializer(serializers.ModelSerializer): 
    class Meta:
        model = City
        fields = ["id", "name", "province"]

# create shop
class ShopCreateSerializer(serializers.ModelSerializer): 
    province_id = serializers.IntegerField(write_only=True)
    city_id = serializers.IntegerField(write_only=True)
    district_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Shop
        fields = [
            "name",
            "phone",
            "address",
            "logo",
            "image_shop",
            "province_id",
            "city_id",
            "district_id",
        ]

    def validate(self, attrs):
        province_id = attrs.get("province_id")
        city_id = attrs.get("city_id")


        if not City.objects.filter(id=city_id, province_id=province_id).exists():
            raise serializers.ValidationError("شهر انتخاب شده متعلق به این استان نیست.")
        
        district_id = attrs.get("district_id")

        if district_id:
            if not District.objects.filter(id=district_id, city_id=city_id).exists():
                raise serializers.ValidationError("منطقه انتخاب شده متعلق به این شهر نیست.")

        return attrs

    def create(self, validated_data):
        province_id = validated_data.pop("province_id")
        city_id = validated_data.pop("city_id")
        district_id = validated_data.pop("district_id", None)

        shop = Shop.objects.create(
            **validated_data,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            active=True,   
        )
        return shop
