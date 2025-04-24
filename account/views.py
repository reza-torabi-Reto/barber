# account/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.db.models import Q
from .forms import ManagerSignUpForm, CustomerSignUpForm, BarberProfileForm, ManagerProfileForm, CustomerProfileForm
from salon.models import Shop, CustomerShop

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

def home(request):
    return render(request, 'account/home.html')

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
        form = ManagerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('account:profile')
    else:
        form = ManagerProfileForm(instance=profile)

    return render(request, 'account/edit_manager_profile.html', {
        'form': form,
    })

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
            Q(customer__phone__icontains=search_query)
        )

    customers_with_joined = [(cs.customer, cs.joined_at) for cs in customer_shops]

    return render(request, 'account/customer_list.html', {
        'shop': shop,
        'customers_with_joined': customers_with_joined,
        'search_query': search_query,
    })

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