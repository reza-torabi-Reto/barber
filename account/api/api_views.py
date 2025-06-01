# account/api_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes, parser_classes

from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from account.models import ManagerProfile
import os
from django.conf import settings


from rest_framework.permissions import IsAuthenticated
from salon.models import Shop
from .serializers import (
    ManagerSignupSerializer, 
    CustomTokenObtainPairSerializer,
    ManagerUserSerializer, 
    ShopSerializer,
    ManagerProfileUpdateSerializer)

#Login
class CustomLoginAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
#Logout
class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"detail": "با موفقیت خارج شدید."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "توکن نامعتبر یا تکراری است."}, status=status.HTTP_400_BAD_REQUEST)

#Register Manager
class ManagerSignupAPIView(APIView):
    def post(self, request):
        serializer = ManagerSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'detail': 'ثبت‌نام با موفقیت انجام شد.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Profile Manager
class ManagerProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'manager':
            return Response({'detail': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)

        user_data = ManagerUserSerializer(user).data
        shops = Shop.objects.filter(manager=user)
        shops_data = ShopSerializer(shops, many=True).data

        return Response({
            'user': user_data,
            'shops': shops_data,
        })

#Edit Profile Manager

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_manager_profile(request):
    if request.user.role != 'manager':
        return Response({'detail': 'Unauthorized'}, status=403)

    try:
        profile = request.user.manager_profile
        old_avatar = profile.avatar if profile.avatar else None
    except ManagerProfile.DoesNotExist:
        return Response({'detail': 'Profile not found'}, status=404)

    serializer = ManagerProfileUpdateSerializer(instance=profile, data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()

        # حذف آواتار قبلی اگر آواتار جدید فرستاده شده
        if 'avatar' in request.FILES and old_avatar:
            old_avatar_path = os.path.join(settings.MEDIA_ROOT, old_avatar.name)
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                except Exception as e:
                    print(f"Error deleting old avatar: {e}")

        return Response(serializer.data)
    return Response(serializer.errors, status=400)
