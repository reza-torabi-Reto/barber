# accounts/api_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ManagerSignupSerializer

class ManagerSignupAPIView(APIView):
    def post(self, request):
        serializer = ManagerSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "مدیر با موفقیت ثبت‌نام شد."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
