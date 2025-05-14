# salon/forms.py
from django import forms
from django.forms import modelformset_factory
from django.utils import timezone  
from datetime import datetime, timedelta
from django.db.models import Sum
from .models import Shop, Service, ShopSchedule, Appointment, AppointmentService,CustomerShop
from account.models import CustomUser, BarberProfile


class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ('name','address', 'phone',)


class ShopEditForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن وضعیت فقط به "باز" و "بسته"
        self.fields['status'].choices = [
            ('open', 'باز'),
            ('close', 'بسته'),
        ]

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('name', 'price', 'duration', 'barber')
        labels = {
            'name': 'نام خدمت',
            'price': 'قیمت (تومان)',
            'duration': 'زمان (دقیقه)',
            'barber': 'آرایشگر',
        }

    def __init__(self, *args, shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        if shop:
            barbers = BarberProfile.objects.filter(shop=shop, status=True)
            self.fields['barber'].queryset = barbers
            # حذف گزینه خالی
            self.fields['barber'].empty_label = None
            # اگر هیچ آرایشگری وجود ندارد، خطا نمایش بده
            if not barbers.exists():
                self.fields['barber'].choices = [('', 'هیچ آرایشگری در دسترس نیست')]
                self.fields['barber'].disabled = True
        else:
            self.fields['barber'].queryset = BarberProfile.objects.none()
            self.fields['barber'].empty_label = None

    def clean_barber(self):
        barber = self.cleaned_data.get('barber')
        if not barber:
            raise forms.ValidationError('لطفاً یک آرایشگر انتخاب کنید.')
        return barber

class ServiceEditForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('name', 'price', 'duration')  # اضافه شد



class ShopScheduleForm(forms.ModelForm):
    class Meta:
        model = ShopSchedule
        fields = ('day_of_week', 'is_open', 'start_time', 'end_time', 'break_start', 'break_end')
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'break_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'break_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ('barber',)

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        self.shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)

        if self.shop:
            self.fields['barber'].queryset = CustomUser.objects.filter(
                role='barber',
                barber_profile__status=True,
                barber_profile__shop=self.shop
            )
        else:
            self.fields['barber'].queryset = CustomUser.objects.none()

        self.fields['barber'].required = True

    def clean(self):
        cleaned_data = super().clean()
        barber = cleaned_data.get('barber')

        if not barber:
            raise forms.ValidationError({'barber': 'لطفاً یک آرایشگر انتخاب کنید.'})

        if self.shop and barber and barber.barber_profile.shop != self.shop:
            raise forms.ValidationError({'barber': 'این آرایشگر متعلق به آرایشگاه انتخاب‌شده نیست.'})
        if not CustomerShop.objects.filter(customer=self.customer, shop=self.shop).exists():
            raise forms.ValidationError('شما عضو این آرایشگاه نیستید.')

        return cleaned_data

#ok version
# class AppointmentForm(forms.ModelForm):
#     services = forms.ModelMultipleChoiceField(
#         queryset=Service.objects.none(),
#         widget=forms.CheckboxSelectMultiple,
#         required=True
#     )

#     class Meta:
#         model = Appointment
#         fields = ('barber', 'services')

#     def __init__(self, *args, **kwargs):
#         self.customer = kwargs.pop('customer', None)
#         self.shop = kwargs.pop('shop', None)
#         super().__init__(*args, **kwargs)

#         if self.shop:
#             self.fields['services'].queryset = Service.objects.filter(shop=self.shop)
#             self.fields['barber'].queryset = CustomUser.objects.filter(
#                 role='barber',
#                 barber_profile__status= True,
#                 barber_profile__shop=self.shop
#             )
#         else:
#             self.fields['services'].queryset = Service.objects.none()
#             self.fields['barber'].queryset = CustomUser.objects.none()

#         self.fields['services'].required = True
#         self.fields['barber'].required = True

#     def clean(self):
#         cleaned_data = super().clean()
#         services = cleaned_data.get('services')
#         barber = cleaned_data.get('barber')

#         if not services:
#             raise forms.ValidationError({'services': 'لطفاً حداقل یک سرویس انتخاب کنید.'})
#         if not barber:
#             raise forms.ValidationError({'barber': 'لطفاً یک آرایشگر انتخاب کنید.'})

#         if self.shop and services:
#             for service in services:
#                 if service.shop != self.shop:
#                     raise forms.ValidationError({'services': f'سرویس {service.name} متعلق به آرایشگاه انتخاب‌شده نیست.'})
#         if self.shop and barber and barber.barber_profile.shop != self.shop:
#             raise forms.ValidationError({'barber': 'این آرایشگر متعلق به آرایشگاه انتخاب‌شده نیست.'})
#         if not CustomerShop.objects.filter(customer=self.customer, shop=self.shop).exists():
#             raise forms.ValidationError('شما عضو این آرایشگاه نیستید.')

#         return cleaned_data

# class AppointmentForm(forms.ModelForm):
#     barber = forms.ModelChoiceField(
#         queryset=BarberProfile.objects.none(),
#         label='آرایشگر',
#         widget=forms.RadioSelect,
#         required=True
#     )
#     services = forms.ModelMultipleChoiceField(
#         queryset=Service.objects.none(),
#         widget=forms.CheckboxSelectMultiple,
#         label='خدمات',
#         required=True
#     )

#     class Meta:
#         model = Appointment
#         fields = ['barber', 'services']

#     def __init__(self, *args, **kwargs):
#         self.customer = kwargs.pop('customer', None)
#         self.shop = kwargs.pop('shop', None)
#         super().__init__(*args, **kwargs)

#         if self.shop:
#             self.fields['barber'].queryset = BarberProfile.objects.filter(shop=self.shop, status=True)
#             self.fields['services'].queryset = Service.objects.filter(shop=self.shop)

#     def clean(self):
#         cleaned_data = super().clean()
#         barber = cleaned_data.get('barber')
#         services = cleaned_data.get('services')

#         if barber and services:
#             for service in services:
#                 if service.barber != barber:
#                     raise forms.ValidationError("همه خدمات باید متعلق به آرایشگر انتخاب‌شده باشند.")
#         return cleaned_data

ShopScheduleFormSet = modelformset_factory(
    ShopSchedule,
    form=ShopScheduleForm,
    fields=('day_of_week', 'is_open', 'start_time', 'end_time', 'break_start', 'break_end'),
    extra=0
)
