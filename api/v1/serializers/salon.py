from rest_framework import serializers
from apps.salon.models import Shop,Province,City,District ,Service, BarberSchedule, Appointment, AppointmentService,CustomerShop
from apps.account.models import CustomUser, BarberProfile
from utils.date_utils import j_convert_appoiment  # تبدیل تاریخ به جلالی
from datetime import  timedelta

#Serializers salon:
class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'phone']

class ShopEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'phone', 'status']
        extra_kwargs = {
            'status': {'required': True}
        }

    def validate_status(self, value):
        if value not in ['open', 'close']:
            raise serializers.ValidationError("وضعیت باید 'open' یا 'close' باشد.")
        return value


class BarberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'phone']

class ServiceListSerializer(serializers.ModelSerializer):
    barber_name = serializers.CharField(source='barber.full_name', read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration', 'barber', 'barber_name']
        extra_kwargs = {
            'barber': {'required': True}
        }

    def validate_barber(self, barber):
        shop = self.context.get('shop')
        if barber.shop != shop or not barber.status or barber.user.must_change_password:
            raise serializers.ValidationError("آرایشگر انتخاب‌شده معتبر نیست.")
        return barber


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration']

class ShopDetailSerializer(serializers.ModelSerializer):
    barbers = serializers.SerializerMethodField()
    active_barbers = serializers.SerializerMethodField()
    services = ServiceSerializer(many=True, read_only=True)

    all_appointment_count = serializers.SerializerMethodField()
    pending_appointment_count = serializers.SerializerMethodField()
    today_appointment_count = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'address', 'phone',
            'barbers', 'active_barbers', 'services',
            'all_appointment_count', 'pending_appointment_count', 'today_appointment_count'
        ]

    def get_barbers(self, obj):
        barbers = CustomUser.objects.filter(barber_profile__shop=obj)
        return BarberSerializer(barbers, many=True).data

    def get_active_barbers(self, obj):
        active_barbers = BarberProfile.objects.active().filter(shop=obj)
        return BarberSerializer([b.user for b in active_barbers], many=True).data

    def get_all_appointment_count(self, obj):
        return obj.appointments.count()

    def get_pending_appointment_count(self, obj):
            return obj.appointments.filter(status='pending').count()

    def get_today_appointment_count(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        return obj.appointments.filter(start_time__date=today).count()

#schedule barber
class BarberProfileMinimalSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = BarberProfile
        fields = ['id', 'user_id', 'full_name']


class BarberScheduleSerializer(serializers.ModelSerializer):
    # قالب نمایش و ورودی زمان‌ها: HH:MM یا HH:MM:SS
    start_time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'], allow_null=True, required=False)
    end_time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'], allow_null=True, required=False)
    break_start = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'], allow_null=True, required=False)
    break_end = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'], allow_null=True, required=False)

    class Meta:
        model = BarberSchedule
        fields = ['id', 'day_of_week', 'is_open', 'start_time', 'end_time', 'break_start', 'break_end']
        read_only_fields = ['day_of_week', 'id']  # روز و id معمولاً ثابتند (مطابق formset وب)

    def validate(self, attrs):
        # attrs ممکنه partial باشه؛ برای بررسی ایمن از instance یا مقادیر ارسال شده استفاده می‌کنیم.
        data = {}
        # gather tentative values (instance fallback)
        instance = getattr(self, 'instance', None)
        def _get(name):
            if name in attrs:
                return attrs.get(name)
            if instance:
                return getattr(instance, name)
            return None

        is_open = _get('is_open') if 'is_open' in attrs or instance is None else _get('is_open')
        start = _get('start_time')
        end = _get('end_time')
        bstart = _get('break_start')
        bend = _get('break_end')

        # اگر باز است، start و end لازمند
        if is_open:
            if not start:
                raise serializers.ValidationError({'start_time': 'زمان شروع الزامی است وقتی روز باز باشد.'})
            if not end:
                raise serializers.ValidationError({'end_time': 'زمان پایان الزامی است وقتی روز باز باشد.'})
            if start >= end:
                raise serializers.ValidationError({'end_time': 'زمان پایان باید بعد از زمان شروع باشد.'})

            # اگر یکی از break ها ارسال شده باشد، هر دو لازمند
            if (bstart and not bend) or (bend and not bstart):
                raise serializers.ValidationError({'break_start': 'هر دو زمان استراحت باید پر شوند یا هیچکدام.'})
            if bstart and bend:
                if not (start <= bstart < bend <= end):
                    raise serializers.ValidationError({'break_start': 'بازه استراحت باید داخل بازه کاری و معتبر باشد.'})
        else:
            # اگر روز بسته است، مقادیر زمان را نپذیر - یا به None تبدیل می‌کنیم
            # (در server-side می‌توانیم آنها را نادیده بگیریم)
            pass

        return attrs

#-- for BookAppointmentAPIView
class BarberWithServicesSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(source="barber_profile.services", many=True)

    class Meta:
        model = CustomUser
        fields = ["id", "nickname", "services"]


#-- 


class AppointmentServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentService
        fields = ['service_id', 'service_name', 'duration', 'price']

    service_id = serializers.IntegerField(source='service.id')
    service_name = serializers.CharField(source='service.name')
    duration = serializers.IntegerField(source='service.duration')
    price = serializers.IntegerField(source='service.price')


class AppointmentCustomerSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    barber_name = serializers.CharField(source='barber.nickname', read_only=True)
    jalali_date = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'shop_name', 'barber_name',
            'start_time', 'end_time', 'jalali_date',
            'status', 'services'
        ]

    def get_jalali_date(self, obj):
        return j_convert_appoiment(obj.start_time)

    def get_services(self, obj):
        services = obj.selected_services.all()
        return AppointmentServiceSerializer(services, many=True).data

# ------------------- سرسالایزرهای اصلی احتمالا ازینجاست
from django.utils import timezone

class AppointmentSerializer(serializers.ModelSerializer):
    # barber_name = serializers.CharField(source='barber.get_full_name', read_only=True)
    barber_name = serializers.SerializerMethodField()
    barber_id = serializers.CharField(source='barber.id', read_only=True)
    # status_barber = serializers.CharField(source='barber.status_barber', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    # تاریخ شمسی و ساعت لوکال
    j_start_date = serializers.SerializerMethodField()
    start_time_str = serializers.SerializerMethodField()
    end_time_str = serializers.SerializerMethodField()
    is_expired=serializers.SerializerMethodField()
    class Meta:
        model = Appointment
        fields = [
            'id',
            'barber_name',
            'barber_id',
            # 'status_barber',
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

        # 👈 اینجا اصلاح اصلی
        try:
            barber_profile = barber_user.barber_profile
        except BarberProfile.DoesNotExist:
            return full_name

        if barber_profile.shop_id == obj.shop_id and barber_profile.status_barber == "invited" :
            return f"{full_name} (آرایشگر دعوت شده)"

        # اگر دیگه به این آرایشگاه وصل نیست
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

        if obj.status != 'pending':
            return False

        now = timezone.localtime()

        # اگر تاریخ قبل از امروز باشد → قطعاً منقضی شده
        if obj.start_time.date() < now.date():
            return True

        # اگر دقیقاً امروز است → ساعت را مقایسه کن
        if obj.start_time.date() == now.date():
            if obj.end_time <= now:
                return True

        return False

# این 3 تا سرالایزرها واسه ای-پی-آی سالن فعاله که بخاطر خطا فعلا از خیرش گذشتم
class BarberDetailSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone')
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = BarberProfile
        fields = ['id', 'name', 'avatar', 'phone', 'status']

    def get_name(self, obj):
        return obj.user.nickname() or obj.user.username

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class ServiceDetailSerializer(serializers.ModelSerializer):
    barber_name = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration', 'barber_name']

    def get_barber_name(self, obj):
        if obj.barber and obj.barber.user:
            return obj.barber.user.nickname() or obj.barber.user.username
        return None

class ShopDetailSerializer(serializers.ModelSerializer):
    barbers = BarberDetailSerializer(many=True, read_only=True, source='barber_shop')  # ← اصلاح شد
    services = ServiceDetailSerializer(many=True, read_only=True)
    logo = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'referral_code', 'active',
            'logo', 'image', 'address', 'phone', 'manager',
            'barbers', 'services'
        ]

    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None

    def get_image(self, obj):
        return obj.image_shop.url if obj.image_shop else None

    def get_manager(self, obj):        
        # چون nickname در مدل user به‌صورت متد تعریف شده نه property
        if hasattr(obj.manager, 'nickname') and callable(obj.manager.nickname()):
            return obj.manager.nickname()
        return obj.manager.username if hasattr(obj.manager, 'username') else None
# for mobile
class CustomerOfSalonSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='customer.id')
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='customer.phone')
    first_name = serializers.CharField(source='customer.first_name')
    last_name = serializers.CharField(source='customer.last_name')
    is_active = serializers.BooleanField()
    joined_at = serializers.SerializerMethodField()
    joined_at_gregorian = serializers.DateTimeField(source='joined_at', read_only=True)  # تاریخ اصلی میلادی
    total_appointments = serializers.SerializerMethodField()  # تعداد نوبت‌ها

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
        shop=obj.shop  # ✅ مستقیماً از فیلد shop مدل Appointment استفاده می‌کنیم
    ).count()

# for mobile
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
# for mobile
class AppointmentDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    barber_name = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    jalali_date = serializers.SerializerMethodField()
    start_time_str = serializers.SerializerMethodField()
    end_time_str = serializers.SerializerMethodField()
    canceled_by_display = serializers.SerializerMethodField()
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
            'status_display',
            'jalali_date',
            'start_time_str',
            'end_time_str',
            'status',
            'canceled_by_display',
            'is_expired',
            'can_cancel'
        ]

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_barber_name(self, obj):
        return obj.barber.get_full_name() or obj.barber.username

    def get_services(self, obj):
        return [s.service.name for s in obj.selected_services.all()]
    
    def get_total_price(self, obj):
        return sum(s.service.price for s in obj.selected_services.all())

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
    
    def get_canceled_by_display(self, obj):
      if obj.status == "canceled" and obj.canceled_by:
          return dict(Appointment._meta.get_field("canceled_by").choices).get(obj.canceled_by)
      return None
    
    def get_is_expired(self, obj):

        if obj.status != 'pending':
            return False

        now = timezone.localtime()

        # اگر تاریخ قبل از امروز باشد → قطعاً منقضی شده
        if obj.start_time.date() < now.date():
            return True

        # اگر دقیقاً امروز است → ساعت را مقایسه کن
        if obj.start_time.date() == now.date():
            if obj.end_time <= now:
                return True

        return False
    
    def get_can_cancel(self, obj):
        if obj.status != 'confirmed':
            return False

        now = timezone.localtime()
        # 1 ساعت قبل از شروع نوبت
        cancel_deadline = obj.start_time - timedelta(hours=1)

        return now < cancel_deadline


# mobile
# SalonTab

# ---------------------------
# 1) Shop Summary Serializer
# ---------------------------
class ShopSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = [
            'id',
            'name',
            'logo',
            # 'referral_code',
            # 'status',
            # 'phone',
        ]


# ---------------------------
# 2) Full Shop Details
# ---------------------------
class ShopDetailSerializer(serializers.ModelSerializer):
    create_date = serializers.SerializerMethodField()
    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'address', 'phone',
            'status', 'active', 'logo', 'image_shop', 'referral_code','create_date'
        ]

    def get_create_date(self, obj):
        return j_convert_appoiment(obj.create_date)

# ---------------------------
# 3) Barber List Serializer
# ---------------------------
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

# ---------------------------
# 4) Service List Serializer
# ---------------------------
from utils.salon_utils import get_active_shop
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


# mobile
# update shop
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

#--------------
# mobile
# set scheduls works barbers:
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

from django.core.exceptions import ValidationError as DjangoValidationError
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

            # 🔥 مدل clean() را صدا می‌زنیم و خطاها را تبدیل به DRF error می‌کنیم
            try:
                schedule_obj.clean()
                schedule_obj.save()
            except DjangoValidationError as e:
                errors.append({day: e.messages})

        if errors:
            raise serializers.ValidationError({"errors": errors})

        return instance
# mobile
# get info barber:
from django.utils.timezone import localdate


class BarberAppointmentStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    canceled = serializers.IntegerField()
    pending = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    today_count = serializers.IntegerField()


class BarberProfileDetailSerializer(serializers.ModelSerializer):
    # اطلاعات یوزر
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
            # "status",
            "status_barber",
            "avatar",
            "bio",
            "shop",

            # user info
            "first_name",
            "last_name",
            "phone",
            "email",
            "date_joined_jalali",

            # stats
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
# mobile
# get list provinces and cities:
class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ["id", "name"]


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

        # city must belong to province
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
            active=True,   # Only 1 shop allowed → auto active
        )
        return shop
