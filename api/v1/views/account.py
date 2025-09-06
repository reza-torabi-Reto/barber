#ChatGPT:
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import login

from apps.account.models import CustomUser, BarberProfile
from apps.salon.models import Shop, CustomerShop
from api.v1.serializers.account import *
from utils.auth_utils import RoleRequired, role_required
from services.invitation_service import invite_or_reinvite_barber_api

import random
import os


#VIEWS:

#-- SignUp OTP Manager & Customer:
class SendOTPView(APIView):
    """
    ارسال OTP برای هر نقش (manager یا customer)
    """
    def post(self, request, role):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        if CustomUser.objects.filter(username=phone).exists():
            return Response({'error': 'کاربری با این شماره قبلاً ثبت‌نام کرده است.'}, status=400)

        otp = str(random.randint(100000, 999999))
        request.session['otp_code'] = otp
        request.session['otp_phone'] = phone
        request.session['otp_role'] = role
        print(f"OTP for {phone}: {otp}")

        return Response({"detail": "کد تایید ارسال شد"}, status=200)


class VerifyOTPView(APIView):
    def post(self, request):
        if 'otp_phone' not in request.session:
            return Response({"detail": "لطفاً ابتدا شماره تلفن را ارسال کنید"}, status=400)
        
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_input = serializer.validated_data['otp_code']
        if otp_input == request.session.get('otp_code'):
            request.session['otp_verified'] = True
            return Response({"message": "کد تایید معتبر است"}, status=200)

        return Response({'error': 'کد تأیید نادرست است.'}, status=400)


class CompleteSignupView(APIView):
    """
    تکمیل ثبت‌نام با نقش از session
    """
    def post(self, request):
        if not request.session.get('otp_verified'):
            return Response({'error': 'مراحل قبلی تأیید نشده‌اند.'}, status=400)
        
        role = request.session.get('otp_role')
        phone = request.session.get('otp_phone')

        serializer = BaseSignupSerializer(
            data=request.data,
            context={'request': request, 'phone': phone, 'role': role}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)

        # پاکسازی session
        for key in ['otp_code', 'otp_phone', 'otp_verified', 'otp_role']:
            request.session.pop(key, None)

        return Response({
            "detail": "ثبت‌نام با موفقیت انجام شد",
            "user_id": user.id
        }, status=200)

# Login----------------------------
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

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_force_password_change(request):
    if not request.user.must_change_password:
        return Response({"detail": "تغییر رمز اجباری نیست."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ForcePasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        request.user.must_change_password = False
        request.user.save()
        update_session_auth_hash(request, request.user)
        return Response({"detail": "رمز شما با موفقیت تغییر یافت."}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Manager----------------------------
class ManagerProfileView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def get(self, request):
        user = request.user
        profile = getattr(user, 'manager_profile', None)
        shops = Shop.objects.filter(manager=user)

        serializer = ManagerFullProfileSerializer({
            "user": user,
            "manager_profile": profile,
            "shops": shops
        }, context={"request": request})

        return Response(serializer.data)

class EditManagerProfileView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def get(self, request):
        profile = request.user.manager_profile
        serializer = ManagerProfileUpdateSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile = request.user.manager_profile
        old_avatar = profile.avatar

        serializer = ManagerProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True  # برای اینکه همه فیلدها اجباری نباشند
        )

        if serializer.is_valid():
            serializer.save()

            if old_avatar and 'avatar' in request.data and old_avatar != profile.avatar:
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, old_avatar.name)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")

            return Response({
                'success': True,
                'avatar_url': profile.avatar.url if profile.avatar else None,
                **serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#-- create barber
class CreateBarberOTPApi(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def post(self, request, shop_id):
        """
        دعوت یا دعوت مجدد آرایشگر توسط مدیر
        """
        
        shop = Shop.objects.filter(id=shop_id, manager=request.user).first()
        if not shop:
            return Response({"error": "آرایشگاه یافت نشد یا شما مالک آن نیستید."},
                        status=status.HTTP_404_NOT_FOUND)
        
        phone = request.data.get('phone')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        is_self = request.data.get('is_self', False)
        
        if is_self:
            print(f"TRUE=== {is_self}")
            already_is_barber = BarberProfile.objects.filter(user=request.user).exists()
            if already_is_barber:
                return Response({"error": "شما قبلاً به عنوان آرایشگر ثبت شده‌اید."},
                                status=status.HTTP_400_BAD_REQUEST)

            BarberProfile.objects.create(user=request.user, shop=shop)
            return Response({"message": "شما به عنوان آرایشگر ثبت شدید."},
                            status=status.HTTP_201_CREATED)
        
        if not phone:
            return Response({"error": "شماره همراه الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        
        status_bool, message = invite_or_reinvite_barber_api(
            shop=shop,
            phone=phone,
            first_name=first_name,
            last_name=last_name
        )


        if status_bool:
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST)

#-- active/deactive barber:
@api_view(['POST'])
@role_required(["manager"])
def toggle_barber_status_api(request, shop_id, barber_id):
    # مطمئن شو مدیر مالک فروشگاهه
    try:
        barber = BarberProfile.objects.get(user_id=barber_id, shop__id=shop_id, shop__manager=request.user)
    except BarberProfile.DoesNotExist:
        return Response({"detail": "آرایشگر یا آرایشگاه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    barber.status = not barber.status
    barber.save()

    return Response({
        "id": barber.id,
        "user_id": barber.user_id,
        "status": barber.status,
        "message": "وضعیت آرایشگر با موفقیت تغییر کرد."
    }, status=status.HTTP_200_OK)

#-- delete barber:
@api_view(['DELETE'])
@role_required(["manager"])
def delete_barber_api(request, shop_id, barber_id):
    try:
        shop = Shop.objects.get(id=shop_id, manager=request.user)
        barber = CustomUser.objects.get(id=barber_id, barber_profile__shop=shop)
    except (Shop.DoesNotExist, CustomUser.DoesNotExist):
        return Response({"detail": "آرایشگاه یا آرایشگر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    # حذف آرایشگر از آرایشگاه (از shop خالی شود)
    barber.barber_profile.shop = None
    barber.barber_profile.save()

    return Response({"message": "آرایشگر با موفقیت حذف شد."}, status=status.HTTP_204_NO_CONTENT)

#-- profile barber:
class BarberProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['barber']

    def get(self, request):
        profile = request.user.barber_profile
        serializer = BarberProfileSerializer(profile)
        return Response(serializer.data)

#-- edite profile barber:
class EditBarberProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['barber']

    def put(self, request):
        profile = request.user.barber_profile
        serializer = BarberEditProfileSerializer(profile, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        profile = request.user.barber_profile
        serializer = BarberEditProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#-- profile customer:
class CustomerProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']


    def get(self, request):
        profile = request.user.customer_profile
        customer_shops = CustomerShop.objects.filter(customer=request.user)
        customer_shop_ids = [cs.shop.id for cs in customer_shops]

        search_query = request.query_params.get('search', '')
        search_results = None
        if search_query:
            search_results = Shop.objects.filter(
                Q(name__icontains=search_query) |
                Q(referral_code__icontains=search_query)
            ).values('id', 'name', 'referral_code')

        data = {
            "profile": CustomerProfileSerializer(profile).data,
            "customer_shops": list(customer_shops.values('shop__id', 'shop__name')),
            "customer_shop_ids": customer_shop_ids,
            "search_query": search_query,
            "search_results": list(search_results) if search_results else [],
        }
        return Response(data)

#-- edit customer profile:
class EditCustomerProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['customer']

    def put(self, request):
        profile = request.user.customer_profile
        serializer = CustomerProfileSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

#-- show list of customers by manager:
# views.py
class CustomerListAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
        customer_shops = CustomerShop.objects.filter(shop=shop).select_related('customer')

        # search
        search_query = request.GET.get('search', '')
        if search_query:
            customer_shops = customer_shops.filter(
                Q(customer__username__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query) |
                Q(customer__phone__icontains=search_query)
            )

        # filter by active/inactive
        is_active_param = request.GET.get('is_active')
        if is_active_param == 'true':
            customer_shops = customer_shops.filter(is_active=True)
        elif is_active_param == 'false':
            customer_shops = customer_shops.filter(is_active=False)

        serializer = CustomerShopSerializer(customer_shops, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

#-- toggle statse customer by manager:
class ToggleCustomerStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def patch(self, request, shop_id, customer_id):
        customer_shop = get_object_or_404(
            CustomerShop,
            customer_id=customer_id,
            shop_id=shop_id,
            shop__manager=request.user
        )
        customer_shop.is_active = not customer_shop.is_active
        customer_shop.save()

        return Response({
            "detail": f"مشتری با موفقیت {'فعال' if customer_shop.is_active else 'غیرفعال'} شد.",
            "customer_id": customer_id,
            "is_active": customer_shop.is_active
        }, status=status.HTTP_200_OK)
