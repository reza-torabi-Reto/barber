# salon/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Shop, Service, ShopSchedule, Appointment, AppointmentService,CustomerShop
from account.models import CustomUser
from datetime import datetime, timedelta
from django.db.models import Sum


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


from django.utils import timezone  # اضافه کردن timezone

class AppointmentForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = Appointment
        fields = ('barber', 'date', 'time')

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        self.shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)

        if self.shop:
            self.fields['services'].queryset = Service.objects.filter(shop=self.shop)
            self.fields['barber'].queryset = CustomUser.objects.filter(
                role='barber',
                barber_profile__shop=self.shop
            )
        else:
            self.fields['services'].queryset = Service.objects.none()
            self.fields['barber'].queryset = CustomUser.objects.none()

        self.fields['services'].required = True
        self.fields['barber'].required = True
        self.fields['date'].required = True
        self.fields['time'].required = True

    def clean(self):
        cleaned_data = super().clean()
        services = cleaned_data.get('services')
        barber = cleaned_data.get('barber')
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')

        if not services:
            raise forms.ValidationError({'services': 'لطفاً حداقل یک سرویس انتخاب کنید.'})
        if not barber:
            raise forms.ValidationError({'barber': 'لطفاً یک آرایشگر انتخاب کنید.'})
        if not date:
            raise forms.ValidationError({'date': 'لطفاً تاریخ را انتخاب کنید.'})
        if not time:
            raise forms.ValidationError({'time': 'لطفاً زمان را انتخاب کنید.'})

        if self.shop and services:
            for service in services:
                if service.shop != self.shop:
                    raise forms.ValidationError({'services': f'سرویس {service.name} متعلق به آرایشگاه انتخاب‌شده نیست.'})
        if self.shop and barber and barber.barber_profile.shop != self.shop:
            raise forms.ValidationError({'barber': 'این آرایشگر متعلق به آرایشگاه انتخاب‌شده نیست.'})
        if not CustomerShop.objects.filter(customer=self.customer, shop=self.shop).exists():
            raise forms.ValidationError('شما عضو این آرایشگاه نیستید.')

        if date and time:
            naive_start_time = datetime.combine(date, time)
            start_time = timezone.make_aware(naive_start_time)
            cleaned_data['start_time'] = start_time
            cleaned_data['customer'] = self.customer

            self.instance.start_time = start_time
            self.instance.customer = self.customer
            self.instance.shop = self.shop
            self.instance.barber = barber

            # محاسبه end_time
            total_duration = services.aggregate(total=Sum('duration'))['total']
            if not total_duration:
                raise forms.ValidationError({'services': 'مدت زمان سرویس‌ها نامعتبر است.'})
            self.instance.end_time = start_time + timedelta(minutes=total_duration)

            # اعتبارسنجی‌های اضافی
            # بررسی تداخل زمانی
            overlapping_appointments = Appointment.objects.filter(
                barber=barber,
                start_time__lt=self.instance.end_time,
                end_time__gt=start_time,
                status__in=['pending', 'confirmed']
            ).exclude(id=self.instance.id)
            if overlapping_appointments.exists():
                raise forms.ValidationError('این بازه زمانی قبلاً رزرو شده است.')

            # بررسی ساعات کاری
            day_of_week = start_time.strftime('%A').lower()
            schedule = ShopSchedule.objects.filter(shop=self.shop, day_of_week=day_of_week).first()
            if not schedule or not schedule.is_open:
                raise forms.ValidationError('آرایشگاه در این روز بسته است.')

            start_time_only = start_time.time()
            end_time_only = self.instance.end_time.time()
            if start_time_only < schedule.start_time or end_time_only > schedule.end_time:
                raise forms.ValidationError('زمان نوبت خارج از ساعات کاری آرایشگاه است.')

            if schedule.break_start and schedule.break_end:
                if (start_time_only >= schedule.break_start and start_time_only < schedule.break_end) or \
                   (end_time_only > schedule.break_start and end_time_only <= schedule.break_end):
                    raise forms.ValidationError('زمان نوبت با زمان استراحت آرایشگاه تداخل دارد.')

            # بررسی زمان گذشته
            if start_time < timezone.now():
                raise forms.ValidationError('نمی‌توانید نوبت برای گذشته رزرو کنید.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data['start_time']
        instance.customer = self.customer
        instance.shop = self.shop
        instance.barber = self.cleaned_data['barber']

        # محاسبه end_time
        total_duration = self.cleaned_data['services'].aggregate(total=Sum('duration'))['total']
        if not total_duration:
            raise ValueError("No valid duration for selected services.")
        instance.end_time = instance.start_time + timedelta(minutes=total_duration)

        if commit:
            instance.save()
            instance.selected_services.all().delete()  # حذف سرویس‌های قبلی
            for service in self.cleaned_data['services']:
                AppointmentService.objects.create(appointment=instance, service=service)
        return instance