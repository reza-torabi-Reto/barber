# account/views.py
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse
import os
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from .forms import ManagerSignUpForm, CustomerSignUpForm, BarberProfileForm, ManagerProfileEditForm, CustomerProfileForm
from .models import ManagerProfile, BarberProfile
from salon.models import Shop, CustomerShop


def home(request):
    return render(request, 'account/home.html')
# ---------- Login Section
class CustomLoginView(LoginView):
    template_name = 'account/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role == 'manager':
                return reverse('account:profile')
            
            elif user.role == 'customer':
                return reverse('account:customer_profile')
            
            elif user.role == 'barber':
                return reverse('account:barber_profile')  # بعداً می‌تونیم یه صفحه برای آرایشگرها بسازیم
        return reverse('account:home')

# ---------- Manager Section
def manager_signup(request):
    if request.method == 'POST':
        form = ManagerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('account:profile')
    else:
        form = ManagerSignUpForm()
    return render(request, 'account/manager_signup.html', {'form': form})


@login_required
def profile(request):
    if request.user.role != 'manager':
        return redirect('home')

    shops = Shop.objects.filter(manager=request.user)
    return render(request, 'account/profile.html', {
        'shops': shops,
        'user': request.user,
        'profile': request.user.manager_profile,
    })


@login_required
def edit_manager_profile(request):
    if request.user.role != 'manager':
        return redirect('home')

    profile = request.user.manager_profile
    if request.method == 'POST':
        form = ManagerProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            # گرفتن نمونه اصلی ManagerProfile از دیتابیس برای آواتار قدیمی
            try:
                old_profile = ManagerProfile.objects.get(pk=profile.pk)
                old_avatar = old_profile.avatar
            except ManagerProfile.DoesNotExist:
                old_avatar = None
            
            old_avatar_path = os.path.join(settings.MEDIA_ROOT, old_avatar.name)
            # اگر فایل جدیدی آپلود شده و آواتار قدیمی وجود دارد
            if 'avatar' in request.FILES and old_avatar:
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, old_avatar.name)
                if os.path.exists(old_avatar_path):
                    try:
                        os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")
            # ذخیره فرم
            form.save()
            messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد.')
            return redirect('account:profile')
    else:
        form = ManagerProfileEditForm(instance=profile, user=request.user)

    return render(request, 'account/edit_manager_profile.html', {
        'form': form,
    })


# ---------- Section Barber
@login_required
def barber_profile(request):
    if request.user.role != 'barber':
        return redirect('home')

    profile = request.user.barber_profile
    return render(request, 'account/barber_profile.html', {
        'user': request.user,
        'profile': profile,
    })

@login_required
def edit_barber_profile(request):
    if request.user.role != 'barber':
        return redirect('home')

    profile = request.user.barber_profile
    if request.method == 'POST':
        form = BarberProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('account:barber_profile')
    else:
        form = BarberProfileForm(instance=profile)

    return render(request, 'account/edit_barber_profile.html', {
        'form': form,
    })


@login_required
def toggle_barber_status(request, barber_id, shop_id):
    if request.user.role != 'manager':
        return redirect('home')
    barber = get_object_or_404(BarberProfile, user_id=barber_id, shop__manager=request.user)

    barber.status = not barber.status
    barber.save()

    return redirect('salon:manage_shop', shop_id=shop_id)

# ---------- Customer Section
def customer_signup(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('account:customer_profile')
    else:
        form = CustomerSignUpForm()
    return render(request, 'account/customer_signup.html', {'form': form})


@login_required
def customer_profile(request):
    if request.user.role != 'customer':
        return redirect('home')

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
def edit_customer_profile(request):
    if request.user.role != 'customer':
        return redirect('home')

    profile = request.user.customer_profile
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('account:customer_profile')
    else:
        form = CustomerProfileForm(instance=profile)

    return render(request, 'account/edit_customer_profile.html', {
        'form': form,
    })


@login_required
def customer_list(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    customer_shops = CustomerShop.objects.filter(shop=shop).select_related('customer')

    # جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        customer_shops = customer_shops.filter(
            Q(customer__username__icontains=search_query) |
            # Q(customer__lastname__icontains=search_query) | # error
            Q(customer__phone__icontains=search_query)
        )

    customers_with_joined = [(cs, cs.customer, cs.joined_at) for cs in customer_shops]

    return render(request, 'account/customer_list.html', {
        'shop': shop,
        'customers_with_joined': customers_with_joined,
        'search_query': search_query,
    })

@login_required
def toggle_customer_status(request, customer_id, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    # پیدا کردن CustomerShop
    customer_shop = get_object_or_404(CustomerShop, customer_id=customer_id, shop_id=shop_id)

    # تغییر وضعیت is_active (برعکس کردن)
    customer_shop.is_active = not customer_shop.is_active
    customer_shop.save()

    # پیام موفقیت
    status_text = 'فعال' if customer_shop.is_active else 'غیرفعال'
    messages.success(request, f'مشتری با موفقیت {status_text} شد.')

    # ریدایرکت به customer_list با حفظ search_query و show_active
    search_query = request.GET.get('search', '')
    show_active = request.GET.get('show_active', 'true')
    url = reverse('account:customer_list', kwargs={'shop_id': shop_id})
    query_params = []
    if search_query:
        query_params.append(f'search={search_query}')
    if show_active:
        query_params.append(f'show_active={show_active}')
    if query_params:
        url += '?' + '&'.join(query_params)

    return redirect(url)

@login_required
def join_shop(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id)
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        CustomerShop.objects.create(customer=request.user, shop=shop)
    return redirect('account:customer_profile')

@login_required
def leave_shop(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id)
    CustomerShop.objects.filter(customer=request.user, shop=shop).delete()
    return redirect('account:customer_profile')