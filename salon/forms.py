# salon/forms.py
from django import forms
from .models import Shop, Service

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone', 'status']
        labels = {
            'name': 'نام آرایشگاه',
            'address': 'آدرس',
            'phone': 'شماره تلفن',
            'status': 'وضعیت',
        }



class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'duration', 'price']
        labels = {
            'name': 'نام خدمت',
            'duration': 'مدت زمان (دقیقه)',
            'price': 'قیمت (تومان)',
        }