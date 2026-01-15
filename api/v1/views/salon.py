from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import status
import jdatetime
from apps.account.permissions import *
from apps.account.models import BarberStatus
from apps.salon.models import Shop, Service, BarberSchedule, CustomerShop,Appointment
from apps.account.models import CustomUser,BarberProfile
from api.v1.serializers.salon import *
from utils.date_utils import j_convert_appoiment
from utils.salon_utils import get_active_shop

#-----------------
# APIs Mobile
#-----------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def has_unread_notifications(request): ###    
    has_unread = request.user.notifications.filter(is_read=False).exists()
    return Response({'has_unread': has_unread})

@api_view(['GET'])
def get_customers_of_active_salon_manager(request): ###
    active_shop = Shop.objects.filter(manager=request.user, active=True).first()
    if not active_shop:
        return Response({'detail': 'هیچ آرایشگاه فعالی پیدا نشد.'}, status=404)

    search_query = request.GET.get("q", "").strip()
    
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
def bulk_update_customers_status(request): ###
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
def update_customer_status(request, customer_id): ###
    active_shop = get_active_shop(request.user) 

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
def bulk_update_appointments(request): ###
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


class CustomerProfileDetailView(APIView): ###
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        shop = get_active_shop(request.user)
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
def manager_appointments_api(request): ###

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


class AppointmentDetailAPIView(RetrieveAPIView): ###
    queryset = Appointment.objects.select_related(
        "customer", "barber", "shop"
    ).prefetch_related(
        "selected_services__service"
    )
    serializer_class = AppointmentDetailSerializer
    permission_classes = [IsAuthenticated]


# get barbers of active salon
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manager_barbers_api(request): ###
    
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

# SalonTab
class HasActiveSalonAPIView(APIView):  ###
    permission_classes = [IsAuthenticated]
    def get(self, request):
        shop = get_active_shop(request.user)
        salon = ""
        if not shop:
            salon = False
        else:
            salon =True
        return Response({
            "has_active_salon": salon
        })

class ShopSummaryAPIView(APIView): ###
    permission_classes = [IsAuthenticated]
    def get(self, request):

        shop = get_active_shop(request.user)
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShopSummarySerializer(shop)
        return Response(serializer.data)


class ShopDetailAPIView(APIView): ###
    permission_classes = [IsAuthenticated, IsManager]
    def get(self, request):
        shop = get_active_shop(request.user)
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShopDetailSerializer(shop)
        return Response(serializer.data)


class BarberListAPIView(APIView): ###
    permission_classes = [IsAuthenticated,IsManager]

    def get(self, request):
        shop = get_active_shop(request.user) 
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        barbers = BarberProfile.objects.filter(shop=shop)
        serializer = BarberListSerializer(barbers, many=True)
        return Response(serializer.data)

class BarberListAddServiceAPIView(APIView): ###
    permission_classes = [IsAuthenticated,IsManager]

    def get(self, request):
        shop = get_active_shop(request.user) 
        if not shop:
            return Response({"detail": "هیچ سالن فعالی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        barbers = BarberProfile.objects.filter(shop=shop).exclude(status_barber=BarberStatus.INVITED)
        serializer = BarberListAddServiceSerializer(barbers, many=True)
        return Response(serializer.data)


class ServiceViewSet(ModelViewSet): ###
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

# update fields shop
class ShopUpdateAPIView(APIView): ###
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopUpdateSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ShopLogoUpdateAPIView(APIView): ###
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopLogoUpdateSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"logo": serializer.data["logo"]})

class UpdateShopImage(APIView): ###
    def patch(self, request):
        shop = get_active_shop(request.user)
        serializer = ShopImageSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"image_shop": serializer.data["image_shop"]})
    
class GetShopDetails(APIView): ###
    def get(self, request):
        shop = get_active_shop(request.user)
        if not shop:
            return Response(
                {"detail": "هیچ سالن فعالی یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ShopDetailSerializer(shop)
        return Response(serializer.data, status=status.HTTP_200_OK)

# set scheduls works barbers
class BarberScheduleAPIView(APIView): ###
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

# get info barber
class BarberProfileDetailAPIView(RetrieveAPIView): ###
    queryset = BarberProfile.objects.select_related("user")
    serializer_class = BarberProfileDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"


class BarberStatusUpdateAPIView(APIView): ###
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

# get list provinces and cities:
class ProvinceListView(APIView): ###
    permission_classes = [AllowAny]

    def get(self, request):
        provinces = Province.objects.all().order_by("name")
        serializer = ProvinceSerializer(provinces, many=True)
        return Response(serializer.data)
    
class CityListView(APIView): ###
    permission_classes = [AllowAny]

    def get(self, request, province_id):
        cities = City.objects.filter(province_id=province_id).order_by("name")
        serializer = CitySerializer(cities, many=True)
        return Response(serializer.data)

# create shop:
class ShopCreateView(APIView): ###
    permission_classes = [IsAuthenticated]

    def post(self, request):
        manager = request.user

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


