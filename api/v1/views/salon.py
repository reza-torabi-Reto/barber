from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.db.models import Count

from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timesince import timesince
import jdatetime
from django.db.models import Q
from rest_framework.parsers import MultiPartParser, FormParser

from apps.salon.models import Shop, Service, BarberSchedule, CustomerShop,Appointment, AppointmentService,Notification
from apps.account.models import CustomUser,BarberProfile
from api.v1.serializers.salon import *
from utils.auth_utils import RoleRequired , role_required
from utils.date_utils import j_convert_appoiment
from utils.salon_utils import get_total_service_duration
from utils.notification_utils import message_nitif
from apps.account.permissions import *
from apps.account.models import BarberStatus
from services.appointment import find_available_time_slots


#Views
#--- create shop
class CreateShopAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def post(self, request):
        serializer = ShopSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(manager=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#--- Dashbord shop
class DashboardShopAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']
    
    serializer_class = ShopDetailSerializer
    lookup_url_kwarg = 'shop_id'

    def get_queryset(self):
        # فقط فروشگاه‌های مدیر خود را دسترسی داشته باشیم
        return Shop.objects.filter(manager=self.request.user)

class ShopEditAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def put(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        serializer = ShopEditSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

#--- schedule barber
DAYS = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']

class BarberScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def _ensure_week_rows(self, shop, barber_profile):
        for day in DAYS:
            BarberSchedule.objects.get_or_create(
                shop=shop,
                barber=barber_profile,
                day_of_week=day,
                defaults={'is_open': False}
            )

    def _ordered_schedules_qs(self, shop, barber_profile):
        whens = [When(day_of_week=day, then=Value(i)) for i, day in enumerate(DAYS)]
        qs = BarberSchedule.objects.filter(shop=shop, barber=barber_profile).annotate(
            sort_order=Case(*whens, output_field=IntegerField())
        ).order_by('sort_order')
        return qs

    def _get_shop_and_barber_from_kwargs(self, request, kwargs):
        shop_id = kwargs.get('shop_id')
        barber_id = kwargs.get('barber_id') or request.query_params.get('barber')
        if not shop_id:
            return None, None, Response({"error": "shop_id لازم است."}, status=status.HTTP_400_BAD_REQUEST)
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        if not barber_id:
            return shop, None, None
        barber = get_object_or_404(BarberProfile, id=barber_id, shop=shop)
        return shop, barber, None

    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/shops/{shop_id}/barber-schedule/{barber_id}/
        یا
        GET /api/v1/shops/{shop_id}/barber-schedule/?barber={barber_id}
        - اگر barber_id ارسال نشود فقط لیست آرایشگرها بازگردانده می‌شود.
        """
        shop, barber, error_resp = self._get_shop_and_barber_from_kwargs(request, kwargs)
        if error_resp:
            return error_resp

        # لیست آرایشگرها
        active_barbers = BarberProfile.objects.active().filter(shop=shop)
        barbers_ser = BarberProfileMinimalSerializer(active_barbers, many=True, context={'request': request})

        if barber is None:
            return Response({'shop_id': shop.id, 'barbers': barbers_ser.data})

        # اطمینان از وجود رکوردهای هفته
        self._ensure_week_rows(shop, barber)

        schedules_qs = self._ordered_schedules_qs(shop, barber)
        schedules_ser = BarberScheduleSerializer(schedules_qs, many=True, context={'request': request})

        return Response({
            'shop_id': shop.id,
            'barbers': barbers_ser.data,
            'selected_barber': BarberProfileMinimalSerializer(barber, context={'request': request}).data,
            'schedules': schedules_ser.data
        })

    def put(self, request, *args, **kwargs):
        """
        PUT /api/v1/shops/{shop_id}/barber-schedule/{barber_id}/
        Body:
        {
          "schedules": [ { "id": 1, "is_open": true, "start_time":"09:00", ... }, ... ]
        }
        """
        shop, barber, error_resp = self._get_shop_and_barber_from_kwargs(request, kwargs)
        if error_resp:
            return error_resp
        if barber is None:
            return Response({"error": "barber_id لازم است (در URL یا query param 'barber')."},
                            status=status.HTTP_400_BAD_REQUEST)

        schedules_data = request.data.get('schedules')
        if not isinstance(schedules_data, list) or not schedules_data:
            return Response({"error": "یک لیست schedules لازم است."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            updated_instances = []
            for item in schedules_data:
                sch_id = item.get('id')
                day = item.get('day_of_week')

                instance = None
                if sch_id:
                    instance = BarberSchedule.objects.filter(id=sch_id, shop=shop, barber=barber).first()
                if not instance and day:
                    instance = BarberSchedule.objects.filter(shop=shop, barber=barber, day_of_week=day).first()

                if not instance:
                    return Response({"error": f"سِدِول با id یا day_of_week مشخص شده یافت نشد: {item}"},
                                    status=status.HTTP_400_BAD_REQUEST)

                serializer = BarberScheduleSerializer(instance, data=item, partial=True, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save()
                updated_instances.append(serializer.instance)

        # بازگردانی لیست مرتب‌شده
        qs = self._ordered_schedules_qs(shop, barber)
        return Response({'message': 'بروزرسانی با موفقیت انجام شد.', 'schedules': BarberScheduleSerializer(qs, many=True).data})


#--Services of barber:
class ServiceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        services = Service.objects.filter(shop=shop)
        serializer = ServiceListSerializer(services, many=True)
        return Response(serializer.data)

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        if not BarberProfile.objects.filter(shop=shop, status=True, user__must_change_password=False).exists():
            return Response({"error": "هیچ آرایشگر فعالی برای این فروشگاه وجود ندارد."},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ServiceListSerializer(data=request.data, context={'shop': shop})
        serializer.is_valid(raise_exception=True)
        service = serializer.save(shop=shop)
        return Response(ServiceListSerializer(service).data, status=status.HTTP_201_CREATED)

class ServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def put(self, request, shop_id, service_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        service = get_object_or_404(Service, id=service_id, shop=shop)
        serializer = ServiceListSerializer(service, data=request.data, partial=True, context={'shop': shop})
        serializer.is_valid(raise_exception=True)
        serializer.save(shop=shop)
        return Response(serializer.data)

    def delete(self, request, shop_id, service_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        service = get_object_or_404(Service, id=service_id, shop=shop)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#-- join customer to shop:
class JoinShopAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
            CustomerShop.objects.create(customer=request.user, shop=shop)
            return Response({"detail": "عضویت در آرایشگاه با موفقیت انجام شد."}, status=status.HTTP_201_CREATED)
        return Response({"detail": "شما قبلاً عضو این آرایشگاه هستید."}, status=status.HTTP_200_OK)
 
 #-- leave customer from shop:
class LeaveShopAPIView(APIView):
   permission_classes = [IsAuthenticated, RoleRequired]
   allowed_roles = ['customer']

   def delete(self, request, shop_id):
       shop = get_object_or_404(Shop, id=shop_id)
       deleted_count, _ = CustomerShop.objects.filter(customer=request.user, shop=shop).delete()
       if deleted_count > 0:
           return Response({"detail": "لغو عضویت با موفقیت انجام شد."}, status=status.HTTP_200_OK)
       return Response({"detail": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_400_BAD_REQUEST)

#-- dashboard shop for customer:
class ShopDashboardCustomerAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        
        # بررسی عضویت مشتری
        if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
            return Response({"detail": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_403_FORBIDDEN)

        shop_customer = get_object_or_404(CustomerShop, customer=request.user, shop=shop)
        barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)

        barbers_data = [
            {
                "id": barber.id,
                "name": f"{barber.first_name} {barber.last_name}",
                "phone": barber.phone
            }
            for barber in barbers
        ]

        return Response({
            "shop_id": shop.id,
            "shop_name": shop.name,
            "joined_at": shop_customer.joined_at,
            "barbers": barbers_data
        }, status=status.HTTP_200_OK)

#-- book appointment for customer:
class BookAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request, shop_id):
        """لیست آرایشگران فعال با خدماتشان را برمی‌گرداند"""
        shop = get_object_or_404(Shop, id=shop_id)

        # بررسی عضویت مشتری
        if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
            return Response({"error": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_403_FORBIDDEN)

        barbers = CustomUser.objects.filter(
            barber_profile__shop=shop,
            barber_profile__status=True
        ).prefetch_related('barber_profile', 'barber_profile__services')

        serializer = BarberWithServicesSerializer(barbers, many=True)
        return Response({"shop": shop.name, "barbers": serializer.data})

    def post(self, request, shop_id):
        """ثبت انتخاب آرایشگر و خدمات"""
        shop = get_object_or_404(Shop, id=shop_id)

        if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
            return Response({"error": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_403_FORBIDDEN)

        barber_id = request.data.get('barber_id')
        service_ids = request.data.get('services', [])

        if not barber_id or not service_ids:
            return Response({"error": "لطفاً یک آرایشگر و حداقل یک خدمت انتخاب کنید."}, status=status.HTTP_400_BAD_REQUEST)

        barber = get_object_or_404(CustomUser, id=barber_id, barber_profile__shop=shop)
        services = Service.objects.filter(id__in=service_ids, shop=shop, barber=barber.barber_profile)

        if not services.exists():
            return Response({"error": "خدمات انتخاب‌شده معتبر نیستند."}, status=status.HTTP_400_BAD_REQUEST)

        # به جای session، داده‌ها را به صورت JSON برمی‌گردانیم تا فرانت نگه دارد
        return Response({
            "shop_id": shop.id,
            "barber_id": barber.id,
            "services": list(services.values("id", "name", "price", "duration"))
        }, status=status.HTTP_200_OK)

#-- select date-time-appointment-barber by customer:
class SelectDateTimeAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def post(self, request):
        shop_id = request.data.get("shop_id")
        barber_id = request.data.get("barber_id")
        service_ids = request.data.get("services", [])

        # بررسی وجود داده‌ها
        if not shop_id or not barber_id or not service_ids:
            return Response({"error": "اطلاعات ناقص ارسال شده است."}, status=status.HTTP_400_BAD_REQUEST)

        # دریافت آرایشگاه و آرایشگر
        shop = get_object_or_404(Shop, id=shop_id)
        barber = get_object_or_404(CustomUser, id=barber_id, barber_profile__shop=shop)

        # بررسی عضویت مشتری
        if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
            return Response({"error": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_403_FORBIDDEN)

        # گرفتن سرویس‌ها
        services = Service.objects.filter(id__in=service_ids, shop=shop, barber=barber.barber_profile)
        if not services.exists():
            return Response({"error": "خدمات انتخاب‌شده معتبر نیستند."}, status=status.HTTP_400_BAD_REQUEST)

        total_duration = get_total_service_duration(services)
        total_price = services.aggregate(total=Sum('price'))['total']
        if total_duration == 0:
            return Response({"error": "مدت زمان سرویس‌ها معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST)

        # برنامه کاری آرایشگر
        schedules = BarberSchedule.objects.filter(
            shop=shop, barber=barber.barber_profile, is_open=True
        )
        working_days = {s.day_of_week: s for s in schedules}

        today = timezone.now().date()
        jalali_dates = []

        for i in range(30):
            date = today + timedelta(days=i)
            day_of_week = date.strftime('%A').lower()
            schedule = working_days.get(day_of_week)

            if not schedule or not schedule.start_time or not schedule.end_time:
                continue

            available_times = find_available_time_slots(date, schedule, barber, total_duration)
            if available_times:
                jalali_dates.append({
                    "gregorian_date": date.isoformat(),  # تاریخ میلادی به صورت رشته
                    "jalali_date": j_convert_appoiment(date),  # تاریخ جلالی
                    "day_of_week": schedule.get_day_of_week_display()  # 🔹 پرانتز اضافه شد
                })
        return Response({
            "shop": shop.name,
            "barber": barber.nickname(),
            "services": list(services.values("id", "name", "price", "duration")),
            "total_duration": total_duration,
            "total_price": total_price,
            "dates": jalali_dates
        }, status=status.HTTP_200_OK)

#-- get free times appointment by customer: 
class GetAvailableTimesAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request):
        shop_id = request.query_params.get('shop_id')
        barber_id = request.query_params.get('barber_id')
        date_str = request.query_params.get('date')
        service_ids = request.query_params.getlist('services')

        if not (shop_id and barber_id and date_str and service_ids):
            return Response({"times": []}, status=status.HTTP_400_BAD_REQUEST)

        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            barber = CustomUser.objects.get(id=barber_id, barber_profile__shop_id=shop_id)
            services = Service.objects.filter(id__in=service_ids, shop_id=shop_id)
            total_duration = get_total_service_duration(services)
        except Exception:
            return Response({"times": []}, status=status.HTTP_400_BAD_REQUEST)

        if total_duration == 0:
            return Response({"times": []}, status=status.HTTP_400_BAD_REQUEST)

        day_of_week = selected_date.strftime('%A').lower()
        try:
            schedule = BarberSchedule.objects.get(
                shop_id=shop_id,
                barber=barber.barber_profile,
                day_of_week=day_of_week,
                is_open=True
            )
        except BarberSchedule.DoesNotExist:
            return Response({"times": []})

        available_times = find_available_time_slots(selected_date, schedule, barber, total_duration)
        return Response({"times": available_times})

# confirm appointment by customer:
class ConfirmAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def post(self, request):
        """
        تایید نوبت توسط مشتری
        Expected JSON:
        {
            "shop_id": 1,
            "barber_id": 3,
            "services": [2, 3],
            "date": "2025-08-15",
            "time": "14:30"
        }
        """
        shop_id = request.data.get("shop_id")
        barber_id = request.data.get("barber_id")
        service_ids = request.data.get("services", [])
        date_str = request.data.get("date")
        time_str = request.data.get("time")

        # اعتبارسنجی اولیه
        if not (shop_id and barber_id and service_ids and date_str and time_str):
            return Response({"error": "اطلاعات ناقص ارسال شده است."}, status=status.HTTP_400_BAD_REQUEST)

        shop = get_object_or_404(Shop, id=shop_id)
        barber = get_object_or_404(CustomUser, id=barber_id, barber_profile__shop=shop)

        # بررسی عضویت مشتری در فروشگاه
        if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
            return Response({"error": "شما عضو این آرایشگاه نیستید."}, status=status.HTTP_403_FORBIDDEN)

        # خدمات معتبر
        services = Service.objects.filter(id__in=service_ids, shop=shop)
        if not services.exists():
            return Response({"error": "خدمات انتخاب شده معتبر نیستند."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            time = datetime.strptime(time_str, "%H:%M").time()
            start_time = timezone.make_aware(datetime.combine(date, time))
        except ValueError:
            return Response({"error": "فرمت تاریخ یا ساعت اشتباه است."}, status=status.HTTP_400_BAD_REQUEST)

        total_duration = services.aggregate(total=Sum('duration'))['total'] or 0
        total_price = services.aggregate(total=Sum('price'))['total'] or 0
        end_time = start_time + timedelta(minutes=total_duration)

        # ایجاد نوبت
        appointment = Appointment.objects.create(
            customer=request.user,
            shop=shop,
            barber=barber,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        for service in services:
            AppointmentService.objects.create(appointment=appointment, service=service)

        # ساخت پیام نوتیفیکیشن (اختیاری برای API)
        message_type = 'co'
        message = message_nitif(appointment, start_time, message_type)
        Notification.objects.create(
            user=shop.manager,
            message=message,
            appointment=appointment,
            type='appointment_confirmed',
        )

        return Response({
            "message": "نوبت با موفقیت ثبت شد.",
            "appointment_id": appointment.id,
            "shop": {"id": shop.id, "name": str(shop.name)},
            "barber": {"id": barber.id, "name": str(barber.nickname() if callable(barber.nickname) else barber.nickname)},
            "services": list(services.values("id", "name", "price", "duration")),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration": total_duration,
            "total_price": total_price,
            "status": appointment.status
        }, status=status.HTTP_201_CREATED)

#-- show list all appointments to customer:
class CustomerAppointmentsAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request):
        appointments = Appointment.objects.filter(
            customer=request.user
        ).order_by('-start_time')

        serializer = AppointmentCustomerSerializer(appointments, many=True, context={'request': request})
        return Response({
            "now": timezone.now(),
            "appointments": serializer.data
        })

#-- show list shop appointments to customer:
class ShopCustomerAppointmentsAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request, shop_id):
        appointments = Appointment.objects.filter(
            customer=request.user,
            shop_id=shop_id
        ).order_by('-start_time')

        serializer = AppointmentCustomerSerializer(appointments, many=True, context={'request': request})
        return Response(serializer.data)

#-- show detail & canceled appointment by customer:
class AppointmentDetailCustomerAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def get(self, request, id):
        appointment = get_object_or_404(Appointment, id=id, customer=request.user)
        serializer = AppointmentCustomerSerializer(appointment)
        return Response(serializer.data)

    def delete(self, request, id):
        """لغو نوبت توسط مشتری"""
        appointment = get_object_or_404(Appointment, id=id, customer=request.user)

        if appointment.status == 'canceled':
            return Response(
                {"detail": "این نوبت قبلاً لغو شده است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if appointment.status in ['pending', 'confirmed']:
            appointment.status = 'canceled'
            appointment.canceled_by = 'customer'
            appointment.save()

            # ارسال اعلان به مدیر سالن
            url = reverse('salon:appointment_detail_customer', args=[appointment.id])
            message = message_nitif(appointment, appointment.start_time, 'cc')
            Notification.objects.create(
                user=appointment.shop.manager,
                message=message,
                appointment=appointment,
                url=url,
                type='appointment_canceled',
            )

            return Response({"detail": "نوبت با موفقیت لغو شد."})

        return Response(
            {"detail": "وضعیت نوبت اجازه لغو نمی‌دهد."},
            status=status.HTTP_400_BAD_REQUEST
        )

#-- show list appointments to manager:
# @api_view(['GET'])
# @role_required(['manager'])
# def api_manager_appointments(request, shop_id):
#     """لیست کلی نوبت‌ها برای مدیر"""
#     shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
#     base_qs = Appointment.objects.filter(shop=shop)
#     today = timezone.now().date()
#     pending_only = request.GET.get('pending')

#     if pending_only == '1':  # فقط در انتظار تأیید
#         appointments = base_qs.filter(status='pending')
#     elif pending_only == '2':  # فقط امروز
#         appointments = base_qs.filter(start_time__date=today)
#     else:
#         appointments = base_qs

#     appointments = appointments.select_related('barber', 'customer').order_by('-start_time')

#     counts = {
#         'pending_count': base_qs.filter(status='pending').count(),
#         'today_count': base_qs.filter(start_time__date=today).count(),
#         'all_count': base_qs.count(),
#     }

#     return Response({
#         'shop': shop.name,
#         'counts': counts,
#         'appointments': AppointmentManagerSerializer(appointments, many=True).data,
#         'now': timezone.now(),
#     })

# #-- show list appointments-by-date to manager:
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def api_manager_appointments_days(request, shop_id):
#     shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
#     appointments = Appointment.objects.filter(shop=shop)
#     j_date_str = request.GET.get('date')
#     status_filter = request.GET.get('status')
#     selected_date = timezone.localdate()
#     # فیلتر تاریخ فقط وقتی که پارامتر date وجود داشته باشه
#     if j_date_str:
#         try:             
#              parts = list(map(int, j_date_str.split('-')))
#             # تشخیص فرمت: اگه بخش اول بزرگ باشه یعنی سال هست
#              if parts[0] > 1400:  # سال-ماه-روز
#                  selected_date = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
#                  appointments = appointments.filter(start_time__date=selected_date)
#                  print(f"SELECTED: {selected_date}")
#              else:  # روز-ماه-سال
#                  selected_date = jdatetime.date(parts[2], parts[1], parts[0]).togregorian()
#                  appointments = appointments.filter(start_time__date=selected_date)
#         except Exception as e:
#             print("Date parse error:", e)
#     else:
#         # اگر تاریخ نیست ولی هیچ فیلتر وضعیت هم نیست → پیش‌فرض امروز
#         if not status_filter:
#             today = timezone.localdate()
#             appointments = appointments.filter(start_time__date=today)
#         else:
#             # فیلتر وضعیت
#             if status_filter in ['pending', 'confirmed', 'completed', 'canceled']:
#                 appointments = appointments.filter(status=status_filter)

#     serializer = AppointmentManagerSerializer(appointments, many=True)
#     response_data = {
#         "appointments": serializer.data,
#         "selected_date": selected_date,
#         "previous_date": selected_date - timedelta(days=1),
#         "next_date": selected_date + timedelta(days=1),
#         "status_filter": status_filter,
#         "now": timezone.now()
#     }

#     return Response(response_data)


# salon/api/views.py
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def manager_appointments_api(request):
#     """
#     API: لیست نوبت‌های آرایشگاه فعال مدیر
#     فیلترها:
#       - ?date=1403-04-07
#       - ?status=pending / confirmed / canceled / completed
#     """

#     user = request.user
#     active_shop = Shop.objects.filter(manager=user, is_active=True).first()
#     if not active_shop:
#         return Response(
#             {"detail": "آرایشگاه فعالی یافت نشد."},
#             status=status.HTTP_404_NOT_FOUND
#         )

#     # 🔹 فیلترهای ورودی
#     j_date_str = request.GET.get('date')
#     status_filter = request.GET.get('status')

#     # 🔹 محدوده تاریخی
#     today = datetime.today().date()
#     if j_date_str:
#         try:
#             selected_date = jdatetime.date(*map(int, j_date_str.split('-'))).togregorian()
#         except Exception:
#             selected_date = today
#     else:
#         selected_date = today

#     start_of_day = datetime.combine(selected_date, datetime.min.time())
#     end_of_day = datetime.combine(selected_date, datetime.max.time())

#     # 🔹 فیلتر اصلی
#     barbers_in_shop = BarberProfile.objects.filter(shop=active_shop).values_list('user_id', flat=True)

#     appointments = Appointment.objects.filter(
#         barber_id__in=barbers_in_shop,
#         start_time__range=(start_of_day, end_of_day)
#     ).select_related('barber__user', 'customer')

#     if status_filter in ['pending', 'confirmed', 'completed', 'canceled']:
#         appointments = appointments.filter(status=status_filter)

#     # 🔹 مرتب‌سازی و خروجی
#     serializer = AppointmentSerializer(appointments.order_by('-start_time'), many=True)
#     return Response({
#         "shop": active_shop.name,
#         "total": appointments.count(),
#         "appointments": serializer.data
#     })



#  سریالیزر توی این جایی تعریف نشده!
#-- detail appointment for manager:
# @api_view(['GET', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def api_appointment_detail_manager(request, id):
#     appointment = get_object_or_404(Appointment, id=id)

#     # بررسی نقش مدیر روی فروشگاه مربوطه
#     if request.user != appointment.shop.manager:
#         return Response({"detail": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

#     # GET → اطلاعات نوبت
#     if request.method == 'GET':
#         serializer = AppointmentManagerSerializer(appointment)
#         return Response({
#             "appointment": serializer.data,
#             "now": timezone.now()
#         })

#     # PATCH → تغییر وضعیت نوبت
#     elif request.method == 'PATCH':
#         action = request.data.get('action')
#         if appointment.status == 'canceled':
#             return Response({"detail": "این نوبت قبلاً لغو شده است."}, status=status.HTTP_400_BAD_REQUEST)

#         if action == 'confirm':
#             appointment.status = 'confirmed'
#             appointment.save()
#             msg_type = 'mo'
#             message_text = "نوبت با موفقیت تایید شد."
#         elif action == 'cancel':
#             appointment.status = 'canceled'
#             appointment.canceled_by = 'manager'
#             appointment.save()
#             msg_type = 'mc'
#             message_text = "نوبت لغو شد."
#         else:
#             return Response({"detail": "عملیات نامعتبر."}, status=status.HTTP_400_BAD_REQUEST)

#         # اعلان به مشتری
#         url = f"/customer/appointments/{appointment.id}/"  # مسیر وب یا API مشتری
#         message = message_nitif(appointment, appointment.start_time, msg_type)
#         Notification.objects.create(
#             user=appointment.customer,
#             message=message,
#             appointment=appointment,
#             url=url,
#             type='appointment_update'
#         )

#         serializer = AppointmentManagerSerializer(appointment)
#         return Response({
#             "detail": message_text,
#             "appointment": serializer.data
#         })
# web
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_notifications(request):
    """
    API برای دریافت نوتیفیکیشن‌های نخوانده کاربر لاگین‌شده
    """
    notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')
    print(f"Notifi api : {notifications}")
    data = [
        {
            'id': noti.id,
            'message': noti.message,
            'created_at': timesince(noti.created_at) + ' پیش',
            'url': noti.url or '',
        }
        for noti in notifications
    ]

    return Response({'notifications': data})



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_salons_manager(request):
    """
    API برای دریافت نوتیفیکیشن‌های نخوانده کاربر لاگین‌شده
    """
    shops = Shop.objects.filter(manager=request.user)
    selected_shop = shops.filter(active= True).values('active')
    print(f"selected_shop : {selected_shop}")
    data = [
        {
            'id': shop.id,
            'name': shop.name,
            'manager': shop.manager.id,
            'active' : shop.active
        }
        for shop in shops
    ]

    return Response({'salons': data, 'selected_shop': selected_shop})


# Mobile APIs -----------------------------------


def get_active_shop(user):
    """دریافت سالنی که برای مدیر فعال شده است."""
    return user.managed_shops.filter(active=True).first()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def has_unread_notifications(request):
    
    print("Notification....")
    has_unread = request.user.notifications.filter(is_read=False).exists()
    return Response({'has_unread': has_unread})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def show_salons_manager(request): 
    # فقط آرایشگاه‌های مدیر لاگین‌شده
    shops = (
        Shop.objects.filter(manager=request.user)
        .annotate(
            count_barber=Count("barber_shop", distinct=True),
            count_customer=Count("customer_memberships", distinct=True),
        )
    )
    data = [
        {
            "id": shop.id,
            "name": shop.name,
            "referral_code": shop.referral_code,
            "manager": shop.manager.id,
            "status": shop.status,
            "logo": shop.logo.url if shop.logo else None,
            "count_barber": shop.count_barber,
            "count_customer": shop.count_customer,
            "active": shop.active
        }
        for shop in shops
    ]
    for shop in shops:
        print(f"Shop: {shop.name}, Active: {shop.active}")
    return Response({"salons": data})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def set_active_salon(request, shop_id):
    
    try:
        shop = Shop.objects.get(id=shop_id, manager=request.user)
    except Shop.DoesNotExist:
        return Response({'error': 'آرایشگاه یافت نشد.'}, status=404)

    # غیرفعال کردن بقیه آرایشگاه‌ها
    Shop.objects.filter(manager=request.user).update(active=False)

    # فعال کردن آرایشگاه انتخاب‌شده
    shop.active = True
    shop.save()

    return Response({'message': f'آرایشگاه "{shop.name}" فعال شد.'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_salon(request):
    try:
        shop = Shop.objects.prefetch_related('services__barber__user', 'barber_shop__user').get(manager=request.user, active=True)
        print(f"get active salon: {shop}")
    except Shop.DoesNotExist:
        return Response({'error': 'سالن یافت نشد یا به شما تعلق ندارد.'}, status=404)

    serializer = ShopDetailSerializer(shop)
    return Response(serializer.data)

@api_view(['GET'])
def get_customers_of_active_salon_manager(request):
    # user = request.user
    active_shop = Shop.objects.filter(manager=request.user, active=True).first()
    if not active_shop:
        return Response({'detail': 'هیچ آرایشگاه فعالی پیدا نشد.'}, status=404)

    search_query = request.GET.get("q", "").strip()
    print(f"Query: {search_query}")
    
    customer_shops = CustomerShop.objects.filter(
        shop=active_shop
    ).select_related('customer')

    if search_query:
        customer_shops = customer_shops.filter(
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )

    serializer = CustomerOfSalonSerializer(customer_shops, many=True)
    return Response({"customers": serializer.data})

# update status group customers
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_customers_status(request):
    active_shop = Shop.objects.filter(manager=request.user, active=True).first()
    if not active_shop:
        return Response({'detail': 'هیچ آرایشگاه فعالی پیدا نشد.'}, status=404)

    customer_ids = request.data.get('customer_ids', [])
    is_active = request.data.get('is_active', None)

    if not isinstance(customer_ids, list) or is_active is None:
        return Response({'detail': 'داده‌های ارسالی معتبر نیستند.'}, status=400)

    updated_count = CustomerShop.objects.filter(
        shop=active_shop, customer_id__in=customer_ids
    ).update(is_active=is_active)

    return Response({
        'message': f'{updated_count} مشتری با موفقیت بروزرسانی شد.',
        'updated_count': updated_count
    }, status=200)

# update status one customer
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_customer_status(request, customer_id):
    active_shop = get_active_shop(request.user) #Shop.objects.filter(manager=request.user, active=True).first()
    # if not active_shop:
    #     return Response({'detail': 'هیچ آرایشگاه فعالی پیدا نشد.'}, status=404)

    # مشتری باید عضو همین آرایشگاه باشد
    membership = CustomerShop.objects.filter(
        shop=active_shop,
        customer_id=customer_id
    ).first()

    if not membership:
        return Response({'detail': 'این مشتری در آرایشگاه شما ثبت نشده است.'}, status=404)

    is_active = request.data.get("is_active")
    if is_active is None:
        return Response({'detail': 'فیلد is_active ارسال نشده است.'}, status=400)

    membership.is_active = bool(is_active)
    membership.save()

    return Response({
        "message": "وضعیت مشتری بروزرسانی شد.",
        "customer_id": customer_id,
        "is_active": membership.is_active
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_appointments(request):
    print("Update Appointment...")
    active_shop = Shop.objects.filter(manager=request.user, active=True).first()
    if not active_shop:
        return Response({"detail": "آرایشگاه فعالی یافت نشد."}, status=404)

    appointment_ids = request.data.get("appointment_ids", [])
    new_status = request.data.get("status")
    if not isinstance(appointment_ids, list) or new_status not in ["pending", "confirmed", "completed", "canceled"]:
        return Response({"detail": "داده‌های ارسالی معتبر نیستند."}, status=400)

    updated = Appointment.objects.filter(
        id__in=appointment_ids,
        shop=active_shop
    ).update(status=new_status)

    return Response({
        "updated_count": updated,
        "message": "وضعیت نوبت‌ها بروزرسانی شد.",
    }, status=200)

# mobile

class CustomerProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        shop = get_active_shop(request.user)
        # 2. وجود مشتری
        customer = get_object_or_404(CustomUser, id=pk, role="customer")

        # 3. بررسی عضویت مشتری در سالن
        membership = get_object_or_404(CustomerShop, customer=customer, shop=shop)

        # 4. آمار نوبت‌ها
        now = timezone.now()
        appointments = Appointment.objects.filter(customer=customer, shop=shop)

        total_completed = appointments.filter(status="completed").count()
        total_canceled  = appointments.filter(status="canceled").count()

        #  pending گذشته رو pending حساب نکن چون expire شدن (تحت نظر خودت)
        total_pending = appointments.filter(
            status="pending",
            start_time__gte=now
        ).count()

        # 5. نزدیک‌ترین نوبت آینده
        future_app = appointments.filter(
            status="pending",
            start_time__gte=now
        ).order_by("start_time").first()

        latest_pending_data = None
        if future_app:
            latest_pending_data = {"appointment_id": future_app.id}

        # 6. ساخت خروجی
        data = {
            "customer_id": customer.id,
            "nickname": customer.nickname(),
            "phone": customer.phone,
            "joined_at": j_convert_appoiment(membership.joined_at),
            "is_active": membership.is_active,

            "total_completed": total_completed,
            "total_canceled": total_canceled,
            "total_pending": total_pending,

            "latest_pending": latest_pending_data,
        }

        serializer = CustomerProfileDetailSerializer(data)
        return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manager_appointments_api(request):

    active_shop = get_active_shop(request.user)

    j_date_str = request.GET.get("date")
    status_filter = request.GET.get("status")
    search = request.GET.get("search", "").strip()
    barber_id = request.GET.get("barber")
    
    base_qs = Appointment.objects.filter(shop=active_shop)

    # ----------------
    # فیلتر تاریخ جلالی
    # ----------------
    if j_date_str:
        try:
            selected_date = jdatetime.date(*map(int, j_date_str.split("-"))).togregorian()
            base_qs = base_qs.filter(start_time__date=selected_date)
        except:
            pass

    # ----------------
    # فیلتر وضعیت نوبت
    # ----------------
    if status_filter in ["pending", "confirmed", "completed", "canceled"]:
        base_qs = base_qs.filter(status=status_filter)

    # ----------------
    # فیلتر آرایشگر
    # ----------------
    if barber_id and barber_id.isdigit():
        base_qs = base_qs.filter(barber_id=barber_id)
    
    # ----------------
    # فیلتر جستجو (نام مشتری)
    # ----------------
    if search:
        base_qs = base_qs.filter(customer__first_name__icontains=search)
        
    appointments = base_qs.select_related("barber", "customer").order_by("-created_at")
    
    serializer = AppointmentSerializer(appointments, many=True)

    return Response({
        "appointments": serializer.data,
        "total": appointments.count(),
    })

# mobile
class AppointmentDetailAPIView(RetrieveAPIView):
    queryset = Appointment.objects.select_related(
        "customer", "barber", "shop"
    ).prefetch_related(
        "selected_services__service"
    )
    serializer_class = AppointmentDetailSerializer
    permission_classes = [IsAuthenticated]


# mobile: get barbers of active salon
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manager_barbers_api(request):
    
    active_shop = get_active_shop(request.user)
    barbers = BarberProfile.objects.filter(shop=active_shop).exclude(status_barber=BarberStatus.INVITED).select_related("user")

    data = [
        {
            "id": barber.user.id,
            "name": barber.user.nickname(),
        }
        for barber in barbers
    ]

    return Response({"barbers": data}, status=200)

# mobile
# SalonTab
class HasActiveSalonAPIView(APIView): ##
    permission_classes = [IsAuthenticated]
    def get(self, request):
        print("Get....")
        shop = get_active_shop(request.user)
        salon = ""
        if not shop:
            salon = False
        else:
            salon =True
        return Response({
            "has_active_salon": salon
        })

class ShopSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):

        shop = get_active_shop(request.user)
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShopSummarySerializer(shop)
        return Response(serializer.data)


class ShopDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        shop = get_active_shop(request.user)
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShopDetailSerializer(shop)
        return Response(serializer.data)


class BarberListAPIView(APIView):
    permission_classes = [IsAuthenticated,IsManager]

    def get(self, request):
        shop = get_active_shop(request.user) 
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        barbers = BarberProfile.objects.filter(shop=shop)
        serializer = BarberListSerializer(barbers, many=True)
        return Response(serializer.data)

class BarberListAddServiceAPIView(APIView):
    permission_classes = [IsAuthenticated,IsManager]

    def get(self, request):
        shop = get_active_shop(request.user) 
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        barbers = BarberProfile.objects.filter(shop=shop).exclude(status_barber=BarberStatus.INVITED)
        serializer = BarberListAddServiceSerializer(barbers, many=True)
        return Response(serializer.data)

# 

class ServiceViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated,IsManager]
    def get_queryset(self):
        shop = get_active_shop(self.request.user)
        if not shop:
            return Service.objects.none()

        queryset = Service.objects.filter(shop=shop)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == "true")

        return queryset

    def get_serializer_class(self):
        
        if self.action in ["list", "retrieve"]:
            return ServiceListSerializer
        return ServiceCreateUpdateSerializer

    def perform_create(self, serializer):
        print("Request data:", self.request.data)
        print("Barber from request:", self.request.data.get('barber'))

        shop = get_active_shop(self.request.user)
        serializer.save(shop=shop)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        service = self.get_object()
        service.is_active = True
        service.save(update_fields=["is_active"])
        return Response({"detail": "Service activated"})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        service = self.get_object()
        service.is_active = False
        service.save(update_fields=["is_active"])
        return Response({"detail": "Service deactivated"})

# class ServiceListAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         shop = get_active_shop(request.user)
#         if not shop:
#             return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

#         services = Service.objects.filter(shop=shop).exclude(
#     barber__status_barber="invited"
# )
#         serializer = ServiceListSerializer(services, many=True)
#         return Response(serializer.data)

# mobile
# update fields shop
class ShopUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopUpdateSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ShopLogoUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopLogoUpdateSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"logo": serializer.data["logo"]})

class UpdateShopImage(APIView):
    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopImageSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"image_shop": serializer.data["image_shop"]})
    
class GetShopDetails(APIView):
    def get(self, request):
        shop = get_active_shop(request.user)

        if not shop:
            return Response(
                {"detail": "هیچ سالن فعالی یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ShopDetailSerializer(shop)
        return Response(serializer.data, status=status.HTTP_200_OK)

#-------------
# mobile:
# set scheduls works barbers
class BarberScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, barber_id):
        barber = BarberProfile.objects.filter(id=barber_id, shop__manager=request.user).first()
        if not barber:
            return Response({"detail": "Barber not found"}, status=404)

        days = [d[0] for d in BarberSchedule.DAY_CHOICES]

        # ایجاد روزهای خالی در صورت نبود
        for d in days:
            BarberSchedule.objects.get_or_create(
                barber=barber,
                shop=barber.shop,
                day_of_week=d,
                defaults={"is_open": False},
            )

        schedules = barber.schedules_barber.all().order_by("id")

        data = {
            "barber_id": barber.id,
            "schedule": BarberDailyScheduleSerializer(schedules, many=True).data
        }
        return Response(data)

    def put(self, request, barber_id):
        barber = BarberProfile.objects.filter(id=barber_id, shop__manager=request.user).first()
        if not barber:
            return Response({"detail": "Barber not found"}, status=404)

        serializer = BarberFullScheduleSerializer(
            barber,
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Schedule updated successfully"})

# mobile
# get info barber
class BarberProfileDetailAPIView(RetrieveAPIView):
    queryset = BarberProfile.objects.select_related("user")
    serializer_class = BarberProfileDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

# api/v1/views/salon.py
# class BarberStatusUpdateAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def patch(self, request, barber_id):
#         barber = get_object_or_404(BarberProfile, id=barber_id)

#         new_status = request.data.get("status")
#         print(f"Status: {new_status}")
#         if new_status is None:
#             return Response(
#                 {"detail": "فیلد status الزامی است."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # تبدیل به بولین
#         if isinstance(new_status, str):
#             new_status = new_status.lower() in ['true', '1', 'yes']

#         barber.status = new_status
#         barber.save(update_fields=["status"])

#         return Response(
#             {
#                 "detail": "وضعیت با موفقیت تغییر کرد.",
#                 "status": barber.status
#             },
#             status=status.HTTP_200_OK
#         )from apps.account.permissions import *

class BarberStatusUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def patch(self, request, barber_id):
        barber = get_object_or_404(BarberProfile, id=barber_id)

        new_status = request.data.get("status_barber")

        if new_status not in [BarberStatus.ACTIVE, BarberStatus.SUSPENDED]:
            return Response(
                {"code": "INVALID_STATUS"},
                status=status.HTTP_400_BAD_REQUEST
            )

        barber.status_barber = new_status
        barber.save(update_fields=["status_barber"])

        return Response({
            "id": barber.id,
            "status_barber": barber.status_barber
        })


# mobile
# get list provinces and cities:
class ProvinceListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        provinces = Province.objects.all().order_by("name")
        serializer = ProvinceSerializer(provinces, many=True)
        return Response(serializer.data)
    
class CityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, province_id):
        cities = City.objects.filter(province_id=province_id).order_by("name")
        serializer = CitySerializer(cities, many=True)
        return Response(serializer.data)

# create shop:
class ShopCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        manager = request.user

        # manager has shop?
        if Shop.objects.filter(manager=manager, active=True).exists():
            return Response(
                {"detail": "شما قبلاً یک آرایشگاه فعال دارید."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ShopCreateSerializer(data=request.data)

        if serializer.is_valid():
            shop = serializer.save(manager=manager)
            return Response(
                {"detail": "آرایشگاه با موفقیت ایجاد شد.", "shop_id": shop.id},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# account/views.py
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        data = {
            "id": user.id,
            "role": user.role,
            "must_change_password": user.must_change_password,
        }

        if user.role == "barber":
            barber = getattr(user, "barber_profile", None)
            data["barber"] = {
                "status": barber.status_barber if barber else None,
                "shop_id": barber.shop_id if barber and barber.shop else None,
            }

        if user.role == "manager":
            data["manager"] = {
                "has_shop": hasattr(user, "shop"),
            }

        return Response(data)
