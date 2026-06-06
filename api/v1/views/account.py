from django.contrib.auth import login
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import random
from apps.account.permissions import *
from apps.account.models import *
from apps.salon.models import *
from api.v1.serializers.account import *
from utils.salon_utils import get_active_shop
from utils.auth_utils import RoleRequired


#========================
# MANAGER ACCOUNT VIEWS
#========================

User = get_user_model()

class ForceChangePasswordView(APIView): 
    permission_classes = [ForcePasswordChangePermission,IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'barber':
            return Response(
                {"error": "این عملیات فقط برای آرایشگران مجاز است."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ForceChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['password1'])
        user.must_change_password = False
        user.save()
        barber = getattr(user, 'barber_profile', None)
        if barber:
            barber.status_barber = BarberStatus.ACTIVE
            barber.save()

        return Response(
            {"detail": "رمز عبور با موفقیت تغییر کرد."},
            status=status.HTTP_200_OK
        )


class SendOTPView(APIView): 
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

        return Response({"detail": "کد تایید ارسال شد"}, status=201)


class VerifyOTPView(APIView): 
    def post(self, request):
        if 'otp_phone' not in request.session:
            return Response({"detail": "لطفاً ابتدا شماره تلفن را ارسال کنید"}, status=400)
        
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_input = serializer.validated_data['otp_code']
        print(f"session_code: {request.session.get('otp_code')} otp: {otp_input}")
        if otp_input == request.session.get('otp_code'):
            request.session['otp_verified'] = True
            return Response({"message": "کد تایید معتبر است"}, status=201)
        return Response({'error': 'کد تأیید نادرست است.'}, status=400)


class CompleteSignupView(APIView): 
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
        for key in ['otp_code', 'otp_phone', 'otp_verified', 'otp_role']:
            request.session.pop(key, None)

        return Response({
            "detail": "ثبت‌نام با موفقیت انجام شد",
            "user_id": user.id
        }, status=201)


class SelfAssignBarberView(APIView): 
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        user = request.user
        shop = get_active_shop(request.user)

        if not shop:
            return Response(
                {"error": "ابتدا باید یک آرایشگاه ایجاد کنید."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SelfAssignBarberSerializer()

        try:
            barber = serializer.save(user=user, shop=shop)
        except serializers.ValidationError as e:
            return Response(
                {"error": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "detail": "شما با موفقیت به‌عنوان آرایشگر این آرایشگاه فعال شدید.",
                "barber_id": barber.id
            },
            status=status.HTTP_200_OK
        )

class SelfLeaveBarber(APIView): 
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        shop = get_active_shop(request.user)

        try:
            barber = BarberProfile.objects.get(
                user=request.user,
                shop=shop
            )
        except BarberProfile.DoesNotExist:
            return Response(
                {"error": "شما آرایشگر این آرایشگاه نیستید."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LeaveBarberSerializer()
        serializer.save(barber)

        return Response(
            {"detail": "شما با موفقیت از نقش آرایشگر این آرایشگاه خارج شدید."},
            status=status.HTTP_200_OK
        )


class InviteBarberView(APIView): 
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        serializer = InviteBarberSerializer(
            data=request.data,
            context={"shop": get_active_shop(request.user)}  
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "آرایشگر با موفقیت دعوت شد."})


class RemoveBarberFromShopView(APIView): 
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request, barber_id):
        shop = get_active_shop(request.user)

        try:
            barber = BarberProfile.objects.select_related("user").get(
                id=barber_id,
                shop=shop
            )
        except BarberProfile.DoesNotExist:
            return Response(
                {"error": "آرایشگر در این آرایشگاه یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )
        now = timezone.now()

        has_active_appointments = Appointment.objects.filter(
            barber=barber.user,
            shop=shop,
            status__in=["pending", "confirmed"],
            start_time__gte=now
        ).exists()

        if has_active_appointments:
            return Response(
                {
                    "error": "BARBER_HAS_ACTIVE_APPOINTMENTS"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RemoveBarberFromShopSerializer()
        serializer.save(barber)

        return Response(
            {"detail": "آرایشگر با موفقیت از آرایشگاه حذف شد."},
            status=status.HTTP_200_OK
        )


# login
class CustomTokenObtainPairView(TokenObtainPairView): 
    serializer_class = CustomTokenObtainPairSerializer

class IsAuthView(APIView): 
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        serializer = IsProfileManagerSerializer(user)
        return Response(
            {
                "status": 200,
                "user": serializer.data
            },
            status=status.HTTP_200_OK
        )


class ManagerProfileApi(APIView): 
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']
    def get(self, request):
        user = request.user
        profile = getattr(user, 'manager_profile', None)
        shops = Shop.objects.filter(manager=user).count()

        serializer = ManagerFullProfileApiSerializer({
            "user": user,
            "manager_profile": profile,
            "shops": shops
        }, context={"request": request})
        return Response(serializer.data)


class ManagerProfileUpdateApi(APIView):  
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def patch(self, request):
        user = request.user
        data = request.data
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()

        profile = getattr(user, 'manager_profile', None)
        if profile:
            profile.bio = data.get('bio', profile.bio)
            profile.save()

        return Response({"success": True, "message": "پروفایل با موفقیت به‌روزرسانی شد"})


class ManagerAvatarUpdateApi(APIView): 
    permission_classes = [IsAuthenticated, RoleRequired]
    allowed_roles = ['manager']

    def patch(self, request):
        user = request.user
        profile = getattr(user, 'manager_profile', None)
        avatar = request.FILES.get('avatar')

        if not avatar:
            return Response({"error": "تصویر ارسال نشده است"}, status=400)

        profile.avatar = avatar
        profile.save()

        serializer = ManagerProfileApiSerializer(profile, context={"request": request})
        return Response({
            "success": True,
            "avatar_url": serializer.data["avatar_url"]
        })


class ChangePasswordView(APIView):  
    permission_classes = [IsAuthenticated]
    def patch(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "گذرواژه با موفقیت تغییر یافت."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
