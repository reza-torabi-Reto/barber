# account/forms.py
from django import forms
from .models import Manager

class ManagerSignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")

    class Meta:
        model = Manager
        fields = ['username', 'phone', 'password']
        labels = {
            'username': 'نام کاربری',
            'phone': 'شماره تلفن',
        }

    def save(self, commit=True):
        manager = super().save(commit=False)
        manager.set_password(self.cleaned_data['password'])  # هش کردن رمز عبور
        manager.role = 'manager'  # تنظیم نقش به مدیر
        if commit:
            manager.save()
        return manager
    
    # account/forms.py
from django import forms
from .models import UserProfile

class BarberSignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")

    class Meta:
        model = UserProfile
        fields = ['username', 'phone', 'email', 'avatar', 'password']
        labels = {
            'username': 'نام کاربری',
            # 'nickname': 'نام مستعار',
            'phone': 'شماره تلفن',
            'email': 'ایمیل',
            'avatar': 'تصویر پروفایل',
            # 'about': 'درباره آرایشگر',
        }

    def save(self, commit=True, shop=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'barber'
        user.is_active = True
        if shop:  # آرایشگاه رو از ویو می‌گیره
            user.shop = shop
        if commit:
            user.save()
        return user
    
class CustomerSignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")

    class Meta:
        model = UserProfile
        fields = ['username', 'nickname', 'phone', 'password']  # فیلدهای کمتر برای مشتری
        labels = {
            'username': 'نام کاربری',
            'nickname': 'نام مستعار',
            'phone': 'شماره تلفن',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'customer'
        user.is_active = True
        if commit:
            user.save()
        return user