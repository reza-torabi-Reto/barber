# salon/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ShopForm, ServiceForm
from .models import Shop, Service
from account.forms import BarberSignUpForm
from account.models import UserProfile



@login_required
def create_shop(request):
    if request.user.role != 'manager':  # فقط مدیر می‌تونه آرایشگاه بسازد
        return redirect('acount:error')  # یا یه صفحه خطا

    if request.method == 'POST':
        form = ShopForm(request.POST)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.manager = request.user  # تنظیم مدیر به کاربر فعلی
            shop.save()  # کد یکتا اینجا خودکار تولید می‌شه
            return redirect('account:profile_manager')  # هدایت به لیست آرایشگاه‌ها
    else:
        form = ShopForm()
    return render(request, 'salon/create_shop.html', {'form': form})

@login_required
def shop_list(request):
    if request.user.role != 'manager':
        return redirect('home')
    user = request.user 
    shops = Shop.objects.filter(manager=request.user)
    return render(request, 'salon/shop_list.html', {'shops': shops, 'user': user})

@login_required
def create_barber(request, shop_id):
    if request.user.role != 'manager':
        return redirect('acount:error')

    # مطمئن می‌شیم آرایشگاه متعلق به مدیر فعلیه
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)

    if request.method == 'POST':
        form = BarberSignUpForm(request.POST, request.FILES)  # request.FILES برای آپلود avatar
        if form.is_valid():
            id_shop = shop.id
            barber = form.save(shop=shop)  # آرایشگاه رو به فرم پاس می‌دیم
            
            return redirect('salon:barber_list', shop_id=id_shop)
    else:
        form = BarberSignUpForm()
    return render(request, 'salon/create_barber.html', {'form': form, 'shop': shop})

@login_required
def barber_list(request, shop_id):
    if request.user.role != 'manager':
        return redirect('account:error')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barbers = UserProfile.objects.filter(role='barber', shop=shop)
    return render(request, 'salon/barber_list.html', {'shop': shop, 'barbers': barbers})


@login_required
def create_service(request, shop_id):
    if request.user.role != 'manager':
        return redirect('account:error')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.shop = shop  # تنظیم آرایشگاه
            service.save()
            return redirect('salon:service_list', shop_id=shop.id)
    else:
        form = ServiceForm()
    return render(request, 'salon/create_service.html', {'form': form, 'shop': shop})

# ویو جدید برای نمایش لیست خدمات
@login_required
def service_list(request, shop_id):
    if request.user.role != 'manager':
        return redirect('account:error')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    services = Service.objects.filter(shop=shop)
    return render(request, 'salon/service_list.html', {'shop': shop, 'services': services})
