from rest_framework import serializers
from salon.models import Shop

class ShopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'phone']
