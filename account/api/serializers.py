# accounts/serializers.py

from rest_framework import serializers
from account.models import CustomUser

class ManagerSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'phone_number', 'full_name']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number'),
            full_name=validated_data.get('full_name'),
            is_barbershop_owner=True,
        )
        return user
