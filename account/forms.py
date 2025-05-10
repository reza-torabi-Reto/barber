from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, ManagerProfile, BarberProfile, CustomerProfile

class ManagerSignUpForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=True)
    avatar = forms.ImageField(required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'phone', 'avatar', 'bio')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'manager'
        if commit:
            user.save()
            ManagerProfile.objects.create(
                user=user,
                avatar=self.cleaned_data.get('avatar'),
                bio=self.cleaned_data.get('bio')
            )
        return user

class CustomerSignUpForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user)
        return user

class BarberSignUpForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=True)
    avatar = forms.ImageField(required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = CustomUser
        fields = ('username','first_name', 'last_name', 'password1', 'password2', 'phone', 'avatar', 'bio')

    def save(self, commit=True, shop=None):
        user = super().save(commit=False)
        user.role = 'barber'
        if commit:
            user.save()
            BarberProfile.objects.create(
                user=user,
                avatar=self.cleaned_data.get('avatar'),
                bio=self.cleaned_data.get('bio'),
                shop=shop
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

class ManagerProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, label='نام')
    last_name = forms.CharField(max_length=150, label='نام خانوادگی')
    email = forms.EmailField(label='ایمیل', required=False)
    address = forms.CharField(max_length=255, required=False, label='نشانی')

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
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['address'].initial = user.address if hasattr(user, 'address') else ''
            self.fields['avatar'].widget.can_delete = False


    def save(self, commit=True):
        # ذخیره ManagerProfile
        profile = super().save(commit=False)
        if commit:
            profile.save()

        # ذخیره CustomUser
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if hasattr(user, 'address'):
            user.address = self.cleaned_data['address']
        if commit:
            user.save()

        return profile

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:  # حداکثر 5 مگابایت
                raise forms.ValidationError('حجم فایل باید کمتر از 5 مگابایت باشد.')
            if not avatar.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError('فقط فرمت‌های PNG و JPG مجاز هستند.')
        return avatar


class CustomerProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=15, required=False)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = CustomerProfile
        fields = ()

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