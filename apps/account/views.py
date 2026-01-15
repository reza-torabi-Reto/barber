# account/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login , logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView
from django.urls import reverse
import os
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
import random
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash

from .forms import *
from .models import *
from apps.salon.models import Shop, CustomerShop
from utils.auth_utils import role_required
from services.invitation_service import invite_or_reinvite_barber

#Views
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'account/change_password.html'
    success_url = reverse_lazy('account:change_password_done')


class CustomPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'account/change_password_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == 'manager':
            context['home_url'] = reverse('account:profile')
        elif user.role == 'barber':
            context['home_url'] = reverse('account:barber_profile')
        elif user.role == 'customer':
            context['home_url'] = reverse('account:customer_profile')
        else:
            context['home_url'] = reverse('account:home')  # برای احتیاط

        return context


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'account/password_reset_form.html'
    email_template_name = 'account/password_reset_email.html'
    subject_template_name = 'account/password_reset_subject.txt'
    success_url = 'done/'
#-------------------------------------------------
def force_password_change(request): #api/v1/views/account/force_password_change_api
    if not request.user.must_change_password:
        return redirect('account:home')

    if request.method == 'POST':
        form = ForcePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "رمز شما با موفقیت تغییر یافت.")
            return redirect('account:barber_profile')  # یا مسیر متناسب با نقش
    else:
        form = ForcePasswordChangeForm(user=request.user)
    return render(request, 'account/force_password_change.html', {'form': form})

# ---------- Login Section
class CustomLoginView(LoginView):
    template_name = 'account/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.must_change_password:
            return reverse('account:force_password_change')  # 👈 ریدایرکت به صفحه تغییر رمز
        
        if user.is_authenticated:
            if user.role == 'manager':
                return reverse('account:profile')
            
            elif user.role == 'customer':
                return reverse('account:customer_profile')
            
            elif user.role == 'barber':
                return reverse('account:barber_profile')  
        return reverse('account:home')




def home(request):
    return render(request, 'account/home.html')

# ---------- Manager ------------
# ذخیره OTP موقتی در session (یا میتونی در DB ذخیره کنی)
def send_otp_code(phone, request):
    otp = str(random.randint(100000, 999999))
    print(f"OTP for {phone}: {otp}")  # برای تست در لاگ
    request.session['otp_code'] = otp
    request.session['otp_phone'] = phone
    return otp

def manager_signup_phone(request):
    if request.method == 'POST':
        form = SignUpPhoneForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            if CustomUser.objects.filter(username=phone).exists():
                messages.error(request, 'کاربری با این شماره قبلاً ثبت‌نام کرده است.')
                return redirect('account:manager_signup_phone')
            send_otp_code(phone, request)
            return redirect('account:manager_verify_otp')
    else:
        form = SignUpPhoneForm()
    return render(request, 'account/manager_signup_phone.html', {'form': form})

# تایید کد otp
def manager_verify_otp(request):
    if request.method == 'POST':
        form = SignUpOTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            if otp_code == request.session.get('otp_code'):
                # OTP صحیح است
                request.session['otp_verified'] = True
                return redirect('account:manager_complete_signup')
            else:
                messages.error(request, 'کد تایید نادرست است.')
    else:
        form = SignUpOTPForm()
    return render(request, 'account/manager_verify_otp.html', {'form': form})

# فرم تکمیل ثبت نام
def manager_complete_signup(request):
    if not request.session.get('otp_verified'):
        return redirect('account:manager_signup_phone')

    phone = request.session.get('otp_phone')
    if request.method == 'POST':
        form = ManagerCompleteSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'manager'
            user.phone = phone
            user.username = phone  # یا هر سیاست دلخواه برای username
            user.save()
            ManagerProfile.objects.create(user=user)
            login(request, user)
            # پاک کردن session های مربوط به otp
            request.session.pop('otp_code', None)
            request.session.pop('otp_phone', None)
            request.session.pop('otp_verified', None)
            return redirect('account:profile')
    else:
        form = ManagerCompleteSignupForm()
    return render(request, 'account/manager_complete_signup.html', {'form': form})


# پروفایل مدیر
@login_required
@role_required(['manager'])
def profile(request):

    shops = Shop.objects.filter(manager=request.user)
    return render(request, 'account/profile.html', {
        'shops': shops,
        'user': request.user,
        'profile': request.user.manager_profile,
    })
# ویرایش مدیر
@login_required
@role_required(['manager'])
def edit_manager_profile(request):
    
    profile = request.user.manager_profile
    if request.method == 'POST':
        form = ManagerProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            form = ManagerProfileEditForm(instance=profile, user=request.user)            
            # رندر همان صفحه با فرم جدید و پیام
            return render(request, 'account/edit_manager_profile.html', {
                'form': form,
                'show_success_message': True  # پرچم برای نمایش پیام
            })
    else:
        form = ManagerProfileEditForm(instance=profile, user=request.user)

    return render(request, 'account/edit_manager_profile.html', {
        'form': form,
    })

# ----------- Barber-----------
User = get_user_model()
@login_required
@role_required(['manager'])
def create_barber_otp(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    already_is_barber = BarberProfile.objects.filter(user=request.user).exists()
    if request.method == 'POST':
        form = BarberCreateForm(request.POST, include_is_self=not already_is_barber)
        if form.is_valid():
            is_self = form.cleaned_data.get('is_self', False)

            if is_self:
                # اگر قبلاً آرایشگر شده باشه، نمی‌ذاریم دوباره ثبت بشه
                if already_is_barber:
                    messages.error(request, "شما قبلاً به عنوان آرایشگر ثبت شده‌اید.")
                    return redirect('salon:manage_shop', shop_id=shop.id)

                BarberProfile.objects.create(user=request.user, shop=shop)
                request.user.save()
                messages.success(request, "شما به عنوان آرایشگر ثبت شدید.")
                return redirect('salon:manage_shop', shop_id=shop.id)
            else:
                phone = form.cleaned_data['phone']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']

                status, message = invite_or_reinvite_barber(
                    request, shop, phone, first_name, last_name
                )
                if status:
                    return redirect('salon:manage_shop', shop_id=shop.id)
                else:
                    form.add_error('phone', message)
    else:
        form = BarberCreateForm(include_is_self=not already_is_barber)

    return render(request, 'account/create_barber_otp.html', {
        'form': form,
        'already_is_barber': already_is_barber,
        'shop': shop
    })

@login_required
@role_required(['barber'])
def barber_profile(request):
    
    profile = request.user.barber_profile
    return render(request, 'account/barber_profile.html', {
        'user': request.user,
        'profile': profile,
    })


@login_required
@role_required(['barber'])
def edit_barber_profile(request):
    profile = request.user.barber_profile
    
    if request.method == 'POST':
        form = BarberProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        
        if form.is_valid():
            # کد حذف آواتار قدیمی...
            try:
                old_profile = BarberProfile.objects.get(pk=profile.pk)
                old_avatar = old_profile.avatar
            except BarberProfile.DoesNotExist:
                old_avatar = None

            if 'avatar' in request.FILES and old_avatar:
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, old_avatar.name)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")
            form.save()
            # به جای ریدایرکت، فرم را با داده‌های جدید رندر کنید
            form = BarberProfileEditForm(instance=request.user.barber_profile, user=request.user)
            
            # رندر همان صفحه با فرم جدید و پیام
            return render(request, 'account/edit_barber_profile.html', {
                'form': form,
                'show_success_message': True  # پرچم برای نمایش پیام
            })
    else:
        form = BarberProfileEditForm(instance=profile, user=request.user)
    
    return render(request, 'account/edit_barber_profile.html', {'form': form, 'show_success_message': False})

#-------------
@login_required
@role_required(['manager'])
def toggle_barber_status(request, barber_id, shop_id):
    
    barber = get_object_or_404(BarberProfile, user_id=barber_id, shop__manager=request.user)
    barber.status = not barber.status
    barber.save()

    return redirect('salon:manage_shop', shop_id=shop_id)

# ---------- Customer Section
def customer_signup_phone(request):
    if request.method == 'POST':
        form = SignUpPhoneForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            if CustomUser.objects.filter(username=phone).exists():
                messages.error(request, 'کاربری با این شماره قبلاً ثبت‌نام کرده است.')
                return redirect('account:customer_signup_phone')
            send_otp_code(phone, request)
            return redirect('account:customer_verify_otp')
    else:
        form = SignUpPhoneForm()
    return render(request, 'account/customer_signup_phone.html', {'form': form})


# تایید کد otp
def customer_verify_otp(request):
    if request.method == 'POST':
        form = SignUpOTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            if otp_code == request.session.get('otp_code'):
                # OTP صحیح است
                request.session['otp_verified'] = True
                return redirect('account:customer_complete_signup')
            else:
                messages.error(request, 'کد تایید نادرست است.')
    else:
        form = SignUpOTPForm()
    return render(request, 'account/customer_verify_otp.html', {'form': form})


# فرم تکمیل ثبت نام
def customer_complete_signup(request):
    if not request.session.get('otp_verified'):
        return redirect('account:customer_signup_phone')

    phone = request.session.get('otp_phone')
    if request.method == 'POST':
        form = CustomerCompleteSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'customer'
            user.phone = phone
            user.username = phone  # یا هر سیاست دلخواه برای username
            user.save()
            CustomerProfile.objects.create(user=user)
            login(request, user)
            # پاک کردن session های مربوط به otp
            request.session.pop('otp_code', None)
            request.session.pop('otp_phone', None)
            request.session.pop('otp_verified', None)
            return redirect('account:customer_profile')
    else:
        form = CustomerCompleteSignupForm()
    return render(request, 'account/customer_complete_signup.html', {'form': form})

#-----------------------------------
@login_required
@role_required(['customer'])
def customer_profile(request):
    
    customer_shops = CustomerShop.objects.filter(customer=request.user)
    customer_shop_ids = [cs.shop.id for cs in customer_shops]

    search_query = request.GET.get('search', '')
    search_results = None
    if search_query:
        search_results = Shop.objects.filter(
            Q(name__icontains=search_query) | Q(referral_code__icontains=search_query)
        )

    return render(request, 'account/customer_profile.html', {
        'user': request.user,
        'profile': request.user.customer_profile,
        'customer_shops': customer_shops,
        'customer_shop_ids': customer_shop_ids,
        'search_query': search_query,
        'search_results': search_results,
    })


@login_required
@role_required(['customer'])
def edit_customer_profile(request):
    
    profile = request.user.customer_profile
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            form = CustomerProfileForm(instance=profile)
            return render(request, 'account/edit_customer_profile.html', {
                'form': form,
                'show_success_message': True  # پرچم برای نمایش پیام
            })
    else:
        form = CustomerProfileForm(instance=profile)

    return render(request, 'account/edit_customer_profile.html', {
        'form': form,
    })


@login_required
@role_required(['manager'])
def customer_list(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    customer_shops = CustomerShop.objects.filter(shop=shop).select_related('customer')

    # گرفتن پارامترهای GET
    search_query = request.GET.get('search', '').strip()
    is_active_param = request.GET.get('is_active', '').lower()

    # فیلتر جستجو
    if search_query:
        customer_shops = customer_shops.filter(
            Q(customer__username__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )

    # فیلتر وضعیت فعال/غیرفعال
    if is_active_param in ['true', 'false']:
        customer_shops = customer_shops.filter(is_active=(is_active_param == 'true'))

    customers_with_joined = [(cs, cs.customer, cs.joined_at) for cs in customer_shops]

    return render(request, 'account/customer_list.html', {
        'shop': shop,
        'customers_with_joined': customers_with_joined,
        'search_query': search_query,
        'is_active_param': is_active_param,  # برای انتخاب در فرم
    })

@login_required
@role_required(['manager'])
def toggle_customer_status(request, customer_id, shop_id):
    customer_shop = get_object_or_404(CustomerShop, customer_id=customer_id, shop_id=shop_id)
    customer_shop.is_active = not customer_shop.is_active
    customer_shop.save()

    status_text = 'فعال' if customer_shop.is_active else 'غیرفعال'
    messages.success(request, f'مشتری با موفقیت {status_text} شد.')

    search_query = request.GET.get('search', '')
    url = reverse('account:customer_list', kwargs={'shop_id': shop_id})
    if search_query:
        url += f'?search={search_query}'
    return redirect(url)



@login_required
@role_required(['customer'])
def join_shop(request, shop_id):
    
    shop = get_object_or_404(Shop, id=shop_id)
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        CustomerShop.objects.create(customer=request.user, shop=shop)
    return redirect('account:customer_profile')

@login_required
@role_required(['customer'])
def leave_shop(request, shop_id):
    
    shop = get_object_or_404(Shop, id=shop_id)
    CustomerShop.objects.filter(customer=request.user, shop=shop).delete()
    return redirect('account:customer_profile')