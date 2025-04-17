# account/views.py
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db.models import Q

from .forms import ManagerSignUpForm, CustomerSignUpForm
from salon.models import Shop, CustomerShop

# این ویو رو می‌تونی شخصی‌سازی کنی
class CustomLoginView(LoginView):
    template_name = 'account/login.html'  # تمپلیت صفحه ورود


def error(request):
    return HttpResponse('error!')

# ویو جدید برای صفحه اصلی
def home(request):
    return render(request, 'account/home.html')

def manager_signup(request):
    if request.method == 'POST':
        form = ManagerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # ذخیره مدیر با نقش 'manager'
            login(request, user)
            return redirect('account:login')  # هدایت به صفحه ورود بعد از ثبت‌نام
    else:
        form = ManagerSignUpForm()
    return render(request, 'account/manager_signup.html', {'form': form})



@login_required
def profile_manager(request):
    if request.user.role != 'manager':  # فقط مدیر می‌تونه پروفایلش رو ببینه
        return redirect('error')  # یا یه صفحه خطا

    shops = Shop.objects.filter(manager=request.user)  # آرایشگاه‌های مدیر فعلی
    return render(request, 'account/profile_manager.html', {'shops': shops})


def customer_signup(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('account:customer_profile')  # هدایت به پروفایل مشتری
    else:
        form = CustomerSignUpForm()
    return render(request, 'account/customer_signup.html', {'form': form})
@login_required
def customer_profile(request):
    if request.user.role != 'customer':
        return redirect('home')

    # لیست آرایشگاه‌های مشتری
    customer_shops = CustomerShop.objects.filter(customer=request.user)
    # لیست IDهای آرایشگاه‌هایی که مشتری عضوشونه
    customer_shop_ids = [cs.shop.id for cs in customer_shops]

    # جستجوی آرایشگاه
    search_query = request.GET.get('search', '')
    search_results = None
    if search_query:
        search_results = Shop.objects.filter(
            Q(name__icontains=search_query) | Q(referral_code__icontains=search_query)
        )

    return render(request, 'account/customer_profile.html', {
        'user': request.user,
        'customer_shops': customer_shops,
        'customer_shop_ids': customer_shop_ids,  # اضافه کردن لیست IDها
        'search_query': search_query,
        'search_results': search_results,
    })

# ویو جدید برای اضافه کردن آرایشگاه به لیست مشتری
@login_required
def join_shop(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id)
    # چک کردن اینکه مشتری قبلاً به این آرایشگاه ملحق نشده باشه
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        CustomerShop.objects.create(customer=request.user, shop=shop)
    return redirect('account:customer_profile')


# ویو جدید برای لغو عضویت
@login_required
def leave_shop(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id)
    # حذف رابطه مشتری و آرایشگاه
    CustomerShop.objects.filter(customer=request.user, shop=shop).delete()
    return redirect('account:customer_profile')