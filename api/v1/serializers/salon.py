from rest_framework import serializers
from apps.salon.models import Shop, Service, BarberSchedule, Appointment, AppointmentService
from apps.account.models import CustomUser, BarberProfile
from utils.date_utils import j_convert_appoiment  # تبدیل تاریخ به جلالی


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

#-- api_manager_appointments, api_manager_appointments_days api-views:
class AppointmentManagerSerializer(serializers.ModelSerializer):
    barber_name = serializers.CharField(source='barber.get_full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    start_time_str = serializers.DateTimeField(source='start_time', format='%Y-%m-%d %H:%M', read_only=True)
    end_time_str = serializers.DateTimeField(source='end_time', format='%Y-%m-%d %H:%M', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'status',
            'barber_name',
            'customer_name',
            'start_time_str',
            'end_time_str',
        ]

