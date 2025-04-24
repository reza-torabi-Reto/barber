# salon/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Shop, Service, ShopSchedule, Appointment
from account.models import CustomUser
import datetime

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ('name',)

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('name', 'price', 'duration')

class BarberSignUpForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    phone = forms.CharField(max_length=15, required=True)
    avatar = forms.ImageField(required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)

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

ShopScheduleFormSet = modelformset_factory(
    ShopSchedule,
    form=ShopScheduleForm,
    fields=('day_of_week', 'is_open', 'start_time', 'end_time', 'break_start', 'break_end'),
    extra=0
)

class AppointmentForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = Appointment
        fields = ('shop', 'service', 'barber', 'date', 'time')

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        # محدود کردن انتخاب آرایشگاه به آرایشگاه‌هایی که مشتری عضو اوناست
        if self.customer:
            self.fields['shop'].queryset = Shop.objects.filter(shop_customers__customer=self.customer)

        # محدود کردن انتخاب سرویس و آرایشگر بر اساس آرایشگاه انتخاب‌شده
        if 'shop' in self.data:
            try:
                shop_id = int(self.data.get('shop'))
                self.fields['service'].queryset = Service.objects.filter(shop_id=shop_id)
                self.fields['barber'].queryset = CustomUser.objects.filter(
                    role='barber',
                    barber_profile__shop_id=shop_id
                )
            except (ValueError, TypeError):
                self.fields['service'].queryset = Service.objects.none()
                self.fields['barber'].queryset = CustomUser.objects.none()
        elif self.instance.pk and self.instance.shop:
            self.fields['service'].queryset = Service.objects.filter(shop=self.instance.shop)
            self.fields['barber'].queryset = CustomUser.objects.filter(
                role='barber',
                barber_profile__shop=self.instance.shop
            )
        else:
            self.fields['service'].queryset = Service.objects.none()
            self.fields['barber'].queryset = CustomUser.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        shop = cleaned_data.get('shop')

        if date and time:
            # ترکیب تاریخ و زمان برای ساخت start_time
            cleaned_data['start_time'] = datetime.datetime.combine(date, time)
            cleaned_data['customer'] = self.customer

            # تنظیم موقت start_time برای اعتبارسنجی
            self.instance.start_time = cleaned_data['start_time']
            self.instance.customer = self.customer

            # فراخوانی اعتبارسنجی مدل
            self.instance.clean()

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data['start_time']
        instance.customer = self.customer
        if commit:
            instance.save()
        return instance