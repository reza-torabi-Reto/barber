from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm,PasswordResetForm
from django.core.exceptions import ValidationError
from .models import CustomUser, ManagerProfile, BarberProfile, CustomerProfile
import re


# forms.py
# بازیابی گذرواژه
class CustomPasswordResetForm(PasswordResetForm):    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not CustomUser.objects.filter(email=email).exists():
            raise ValidationError("این نشانی رایانامه در سیستم ثبت نشده است.")
        return email

# ------------- Sign_Up Manager OTP ------------
# فرم شماره تلفن برای شروع ثبت‌نام:
class SignUpPhoneForm(forms.Form):
    phone = forms.RegexField(
        regex=r'^\d{10,15}$',
        error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},
        label='شماره همراه'
    )
# فرم کد otp
class SignUpOTPForm(forms.Form):
    otp_code = forms.CharField(max_length=6, label='کد تایید')

# فرم تکمیل ثبت نام مدیر
class ManagerCompleteSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, label='رایانامه')
    first_name = forms.CharField(max_length=30, label='نام')
    last_name = forms.CharField(max_length=30, label='نام خانوادگی')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return email


class CustomerCompleteSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, label='نام')
    last_name = forms.CharField(max_length=30, label='نام خانوادگی')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name','password1', 'password2')

 
# ----------- Sign-Up Barber OTP --------------
class BarberCreateForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone = forms.RegexField(
        regex=r'^\d{10,15}$',
        required=False,
        error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},
        label='شماره همراه'
    )
    is_self = forms.BooleanField(required=False, label='من خودم می‌خواهم آرایشگر این آرایشگاه باشم.')

    def __init__(self, *args, include_is_self=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not include_is_self:
            self.fields.pop('is_self')

    def clean(self):
        cleaned_data = super().clean()
        is_self = cleaned_data.get('is_self')

        # اگر فیلد is_self حذف شده باشه، مقدارش None میشه، پس باید شرط زیر رو امن‌تر بنویسیم
        if not is_self:
            if not cleaned_data.get('phone'):
                self.add_error('phone', 'شماره تلفن الزامی است.')
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', 'نام الزامی است.')
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', 'نام خانوادگی الزامی است.')


from django import forms
from django.contrib.auth.forms import SetPasswordForm

class ForcePasswordChangeForm(SetPasswordForm):
    new_password1 = forms.CharField(label="رمز عبور جدید",widget=forms.PasswordInput,strip=False,)
    new_password2 = forms.CharField(label="تکرار رمز عبور جدید",strip=False,widget=forms.PasswordInput,)

#----------------------
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="گذرواژه فعلی",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'گذرواژه فعلی'})
    )
    new_password1 = forms.CharField(
        label="گذرواژه جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'گذرواژه جدید'})
    )
    new_password2 = forms.CharField(
        label="تکرار گذرواژه جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'تکرار گذرواژه جدید'})
    )


class ManagerProfileEditForm(forms.ModelForm):
    username = forms.CharField(disabled=True, label='نام کاربری')
    phone = forms.RegexField(regex=r'^\d{10,15}$',error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},label='شماره همراه')
    first_name = forms.CharField(max_length=30, label='نام')
    last_name = forms.CharField(max_length=150, label='نام خانوادگی')
    email = forms.EmailField(required=True, label='ایمیل')

    class Meta:
        model = ManagerProfile
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'avatar': forms.FileInput(attrs={'accept': 'image/png,image/jpeg'}),  # غیرفعال کردن Clear
            }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # گرفتن کاربر برای مقداردهی اولیه
        super().__init__(*args, **kwargs)
        self.user = user  # ✅ این خط رو اضافه کن
        if user:
            self.fields['username'].initial =user.username
            self.fields['phone'].initial =user.phone
            self.fields['first_name'].initial =user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['avatar'].widget.can_delete = False


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:  # حداکثر 5 مگابایت
                raise forms.ValidationError('حجم فایل باید کمتر از 5 مگابایت باشد.')
            if not avatar.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError('فقط فرمت‌های PNG و JPG مجاز هستند.')
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        self.user.phone = self.cleaned_data['phone']
        if commit:
            self.user.save()
            profile.save()
        return profile

    


class CustomerSignUpForm(UserCreationForm):
    # phone = forms.RegexField(regex=r'^\d{10,15}$',error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},label='شماره همراه')
    # email = forms.EmailField(required=True, label='رایانامه')
    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user)
        return user

class BarberSignUpForm(UserCreationForm):
    phone = forms.CharField(max_length=15,required=True,label='شماره تلفن')

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'phone', 'password1', 'password2')
        labels = {
            'username': 'نام کاربری',
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'password1': 'گذرواژه',
            'password2': 'تأیید گذرواژه',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username

    def save(self, commit=True, shop=None):
        user = super().save(commit=False)
        user.role = 'barber'
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
            # ایجاد پروفایل آرایشگر
            if shop:
                BarberProfile.objects.create(
                    user=user,
                    shop=shop,
                    status=True
                )
        return user


class BarberProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=15, required=False)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = BarberProfile
        fields = ('avatar', 'bio')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['phone'].initial = self.instance.user.phone
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.phone = self.cleaned_data['phone']
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
            profile.save()
        return profile


class BarberProfileEditForm(forms.ModelForm):
    username = forms.CharField(disabled=True, label='نام کاربری')
    phone = forms.RegexField(
        regex=r'^\d{10,15}$',
        error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},
        label='شماره همراه'
    )
    first_name = forms.CharField(max_length=30, label='نام')
    last_name = forms.CharField(max_length=150, label='نام خانوادگی')
    email = forms.EmailField(required=True, label='ایمیل')

    class Meta:
        model = BarberProfile
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'avatar': forms.FileInput(attrs={'accept': 'image/png,image/jpeg'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['username'].initial = user.username
            self.fields['phone'].initial = user.phone
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['avatar'].widget.can_delete = False

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError('حجم فایل باید کمتر از ۵ مگابایت باشد.')
            if not avatar.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError('فقط فرمت‌های PNG و JPG مجاز هستند.')
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        self.user.phone = self.cleaned_data['phone']
        if commit:
            self.user.save()
            profile.save()
        return profile



class CustomerProfileForm(forms.ModelForm):
    username = forms.CharField(disabled=True, label='نام کاربری')
    phone = forms.RegexField(
        regex=r'^\d{10,15}$',
        error_messages={'invalid': 'شماره تلفن باید فقط شامل اعداد و حداقل 10 رقم باشد.'},
        label='شماره همراه'
    )
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = CustomerProfile
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['username'].initial = self.instance.user.username
            self.fields['phone'].initial = self.instance.user.phone
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.phone = self.cleaned_data['phone']
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
            profile.save()
        return profile