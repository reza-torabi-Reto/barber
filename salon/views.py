from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum
from datetime import datetime, timedelta, timezone
from django.utils import timezone
from django.contrib import messages
from extensions.utils import j_convert_appoiment
from account.models import CustomUser, BarberProfile
from account.forms import BarberSignUpForm
from .utils.appointment_utils  import get_total_service_duration, find_available_time_slots
from .forms import ShopForm, ServiceForm, ShopScheduleFormSet, AppointmentService, ShopEditForm
from .models import Shop, Service, CustomerShop, ShopSchedule, Appointment


# ================ Manager Section ================
# صفحه ایجاد آرایشگاه توسط مدیر
@login_required
def create_shop(request):
    if request.user.role != 'manager':
        return redirect('home')

    if request.method == 'POST':
        form = ShopForm(request.POST)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.manager = request.user
            shop.save()
            return redirect('account:profile')
    else:
        form = ShopForm()
    return render(request, 'salon/create_shop.html', {'form': form})

# صفحه اطلاعات آرایشگاه برای مدیر
@login_required
def manage_shop(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)
    services = Service.objects.filter(shop=shop)

    base_qs = Appointment.objects.filter(shop=shop)
    all_appointment_count = base_qs.filter().count()
    pending_appointment_count = base_qs.filter(status='pending').count()
    print(f"Date now: {timezone.now().date()}")
    today_appointment_count = base_qs.filter(start_time__date=timezone.now().date()).count()
    return render(request, 'salon/manage_shop.html', {
        'shop': shop,
        'barbers': barbers,
        'services': services,
        'all_appointment_count':all_appointment_count,
        'pending_appointment_count': pending_appointment_count,
        'today_appointment_count': today_appointment_count,
    })

# ویرایش آرایشگاه توسط مدیر
@login_required
def edit_shop(request, shop_id):
    
    if request.user.role != 'manager':
        return redirect('home')
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)

    if request.method == 'POST':
        form = ShopEditForm(request.POST, instance=shop)
        if form.is_valid():
            form.save()
            return redirect('salon:manage_shop', shop_id=shop.id)  # مسیر مورد نظر خودت
    else:
        form = ShopEditForm(instance=shop)

    return render(request, 'salon/edit_shop.html', {'form': form, 'shop': shop})

# صفحه تعیین روزها/ساعت های کاری توسط مدیر
@login_required
def manage_schedule(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    days = [
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
    ]

    # اگر برای روزی تنظیماتی وجود نداشته باشه، یه نمونه جدید با is_open=False می‌سازیم
    for day in days:
        ShopSchedule.objects.get_or_create(
            shop=shop,
            day_of_week=day,
            defaults={'is_open': False}
        )

    # دریافت همه برنامه‌ها (به صورت QuerySet)
    schedules = ShopSchedule.objects.filter(shop=shop)

    if request.method == 'POST':
        formset = ShopScheduleFormSet(request.POST, queryset=schedules)
        if formset.is_valid():
            formset.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        formset = ShopScheduleFormSet(queryset=schedules)

    # جفت کردن فرم‌ها و نمونه‌ها
    form_schedule_pairs = list(zip(formset.forms, schedules))

    # تعریف ترتیب دلخواه روزها (شنبه تا جمعه)
    desired_order = {
        'saturday': 0,  # شنبه
        'sunday': 1,    # یک‌شنبه
        'monday': 2,    # دوشنبه
        'tuesday': 3,   # سه‌شنبه
        'wednesday': 4, # چهارشنبه
        'thursday': 5,  # پنج‌شنبه
        'friday': 6,    # جمعه
    }

    # مرتب‌سازی form_schedule_pairs بر اساس ترتیب دلخواه
    form_schedule_pairs = sorted(form_schedule_pairs, key=lambda x: desired_order[x[1].day_of_week])

    return render(request, 'salon/manage_schedule.html', {
        'shop': shop,
        'formset': formset,
        'form_schedule_pairs': form_schedule_pairs,
    })

# ایجاد آرایشگر توسط مدیر
@login_required
def create_barber(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')
    print('1')
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    if request.method == 'POST':
        form = BarberSignUpForm(request.POST) #->, request.FILES
        print('2')
        if form.is_valid():
            print('3')
            form.save(shop=shop)
            return redirect('salon:manage_shop', shop_id=shop.id)
        else:
            print('Form errors:', form.errors)  # چاپ خطاها برای دیباگ
    else:
        form = BarberSignUpForm()

    return render(request, 'salon/create_barber.html', {'form': form, 'shop': shop})

# حذف آرایشگر از آرایشگاه توسط مدیر
@login_required
def delete_barber(request, shop_id, barber_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barber = get_object_or_404(CustomUser, id=barber_id, role='barber', barber_profile__shop=shop)
    barber.barber_profile.shop = None
    barber.barber_profile.save()
    return redirect('salon:manage_shop', shop_id=shop.id)

# لیست نوبت های یک آرایشگر  توسط مدیر
@login_required
def barber_appointments(request):
    if request.user.role != 'barber':
        return redirect('home')

    appointments = Appointment.objects.filter(barber=request.user).order_by('-start_time')
    return render(request, 'salon/barber_appointments.html', {'appointments': appointments})

# ایجاد خدمت توسط مدیر
@login_required
def create_service(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    # بررسی وجود آرایشگر
    has_barbers = BarberProfile.objects.filter(shop=shop, status=True).exists()

    if request.method == 'POST':
        form = ServiceForm(request.POST, shop=shop)
        if has_barbers and form.is_valid():
            service = form.save(commit=False)
            service.shop = shop
            service.barber = form.cleaned_data['barber']
            service.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ServiceForm(shop=shop)

    return render(request, 'salon/create_service.html', {
        'form': form,
        'shop': shop,
        'has_barbers': has_barbers,
    })

# ویرایش خدمت توسط مدیر
@login_required
def edit_service(request, shop_id, service_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)
    has_barbers = BarberProfile.objects.filter(shop=shop, status=True).exists()

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service, shop=shop)
        if form.is_valid():
            service = form.save(commit=False)
            service.shop = shop
            # آرایشگر تغییر نکند (از مقدار فعلی استفاده می‌شود)
            service.barber = service.barber  # یا نادیده گرفته می‌شود چون در فرم غیرفعال است
            service.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ServiceForm(instance=service, shop=shop)

    return render(request, 'salon/edit_service.html', {
        'form': form,
        'shop': shop,
        'service': service,
        'has_barbers': has_barbers,
    })

# حذف خدمت توسط مدیر
@login_required
def delete_service(request, shop_id, service_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)
    service.delete()
    return redirect('salon:manage_shop', shop_id=shop.id)

# نمایش نوبت ها برای مدیر

@login_required
def manager_appointments(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    base_qs = Appointment.objects.filter(shop=shop)
    pending_only = request.GET.get('pending') 
    if pending_only=='1':
        appointments = base_qs.filter(shop=shop, status='pending').order_by('-start_time') 
    elif pending_only=='2':
        appointments = base_qs.filter(shop=shop, start_time__date=timezone.now().date()).order_by('-start_time') 
    else:
        appointments = base_qs.filter(shop=shop).order_by('-start_time') 

    return render(request, 'salon/manager_appointments.html', {
        'shop': shop,
        'appointments': appointments
    })
# تایید یک نوبت توسط مدیر
@login_required
def confirm_appointment_manager(request, id):
    if request.user.role != 'manager':
        return redirect('home')

    appointment = get_object_or_404(Appointment, id=id)

    if request.method == 'POST':
        appointment.status = 'confirmed'
        appointment.save()
        messages.success(request, 'نوبت با موفقیت تایید شد.')
        shop_id = appointment.shop.id
        url = reverse('salon:manager_appointments', args=[shop_id])
        return redirect(url)  

    return render(request, 'salon/confirm_appointment_manager.html', {'appointment': appointment})

# ================ Customer Section ================
#نمایش نوبت ها برای مشتری
@login_required
def customer_appointments(request):
    if request.user.role != 'customer':
        return redirect('home')
    
    appointments = Appointment.objects.filter(customer=request.user).order_by('-start_time')
    return render(request, 'salon/customer_appointments.html', {'appointments': appointments})

def shop_customer_appointments(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')
    
    appointments = Appointment.objects.filter(customer=request.user, shop_id=shop_id).order_by('-start_time')
    
    return render(request, 'salon/customer_appointments.html', {'appointments': appointments})


# صفحه انتخاب آرایشگر و خدمات توسط مشتری
@login_required
def book_appointment(request, shop_id):
    if request.user.role != 'customer':
        return redirect('account:customer_profile')

    # بررسی عضویت مشتری در آرایشگاه
    shop = get_object_or_404(Shop, id=shop_id)
    if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
        return redirect('account:customer_profile')

    # دریافت آرایشگران فعال آرایشگاه
    barbers = CustomUser.objects.filter(role='barber',barber_profile__shop=shop,barber_profile__status=True).prefetch_related('barber_profile', 'barber_profile__services')
    print(f"++Barbers: {barbers}+++")
    if request.method == 'POST':
        barber_id = request.POST.get('barber_id')
        service_ids = request.POST.getlist('services')  # دریافت لیست خدمات انتخاب‌شده

        if not barber_id or not service_ids:
            return render(request, 'salon/book_appointment.html', {
                'shop': shop,
                'barbers': barbers,
                'error': 'لطفاً یک آرایشگر و حداقل یک خدمت انتخاب کنید.'
            })

        # بررسی معتبر بودن آرایشگر
        barber = get_object_or_404(CustomUser, id=barber_id, role='barber', barber_profile__shop=shop)
        services = Service.objects.filter(id__in=service_ids, shop=shop, barber=barber.barber_profile)

        if not services.exists():
            return (request, 'salon/book_appointment.html', {
                'shop': shop,
                'barbers': barbers,
                'error': 'خدمات انتخاب‌شده معتبر نیستند.'
            })

        # ذخیره اطلاعات در سشن برای استفاده در ویو بعدی
        request.session['appointment_data'] = {
            'shop_id': shop.id,
            'barber_id': barber.id,
            'services': [str(service.id) for service in services]
        }
        return redirect('salon:select_date_time')

    return render(request, 'salon/book_appointment.html', {
        'shop': shop,
        'barbers': barbers,
    })

# گرفتن اطلاعات سرویس‌ها در صفحه book_appointment
def get_shop_details(request):
    shop_id = request.GET.get('shop_id')
    if not shop_id:
        return JsonResponse({'services': [], 'barbers': []})

    services = Service.objects.filter(shop_id=shop_id).values('id', 'name', 'price', 'duration')
    barbers = CustomUser.objects.filter(role='barber',barber_profile__shop_id=shop_id).values('id', 'username')

    return JsonResponse({
        'rvices': list(services),
        'barbers': list(barbers),
    })

# صفحه تعیین روز/ساعت نوبت توسط 
@login_required
def select_date_time(request):
    if request.user.role != 'customer':
        return redirect('home')
    
    appointment_data = request.session.get('appointment_data')
    if not appointment_data:
        return redirect('account:customer_profile')

    shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
    services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
    barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)

    total_duration = get_total_service_duration(services)
    if total_duration == 0:
        return render(request, 'salon/select_date_time.html', {
            'shop': shop,
            'services': services,
            'barber': barber,
            'dates': [],
            'appointment_data': appointment_data,
            'total_duration': total_duration,
            'error': 'مدت زمان سرویس‌ها معتبر نیست.'
        })

    schedules = ShopSchedule.objects.filter(shop=shop, is_open=True)
    working_days = {s.day_of_week: s for s in schedules}
    
    today = timezone.now().date()
    jalali_dates = []

    for i in range(8):
        date = today + timedelta(days=i)
        day_of_week = date.strftime('%A').lower()
        schedule = working_days.get(day_of_week)
        if not schedule or not schedule.start_time or not schedule.end_time:
            continue

        available_times = find_available_time_slots(date, schedule, barber, total_duration)
        if available_times:
            jalali_dates.append({
                'gregorian_date': date,
                'jalali_date': j_convert_appoiment(date),
                'day_of_week': schedule.get_day_of_week_display(),
            })

    return render(request, 'salon/select_date_time.html', {
        'shop': shop,
        'barber': barber,
        'services': services,
        'total_duration': total_duration,
        'dates': jalali_dates,
        'appointment_data': appointment_data,
        'error': 'هیچ روز آزادی برای رزرو در ۸ روز آینده در دسترس نیست.' if not jalali_dates else None,
    })

# نمایش ساعت های خالی روزهای هفته در صفحه:(select_date_time) 
@login_required
def get_available_times(request):
    
    if request.user.role != 'customer':
        return redirect('home')
    
    shop_id = request.GET.get('shop_id')
    barber_id = request.GET.get('barber_id')
    date_str = request.GET.get('date')
    service_ids = request.GET.getlist('services')

    if not (shop_id and barber_id and date_str and service_ids):
        return JsonResponse({'times': []}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        barber = CustomUser.objects.get(id=barber_id, role='barber', barber_profile__shop_id=shop_id)
        services = Service.objects.filter(id__in=service_ids, shop_id=shop_id)
        total_duration = get_total_service_duration(services)
    except Exception:
        return JsonResponse({'times': []}, status=400)

    if total_duration == 0:
        return JsonResponse({'times': []}, status=400)

    day_of_week = selected_date.strftime('%A').lower()
    try:
        schedule = ShopSchedule.objects.get(shop_id=shop_id, day_of_week=day_of_week, is_open=True)
    except ShopSchedule.DoesNotExist:
        return JsonResponse({'times': []})

    available_times = find_available_time_slots(selected_date, schedule, barber, total_duration)
    return JsonResponse({'times': available_times})

# صفحه تایید نوبت توسط 
@login_required
def confirm_appointment(request):
    appointment_data = request.session.get('appointment_data')
    if not appointment_data:
        return redirect('account:customer_profile')

    shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
    services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
    barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    if not (date_str and time_str):
        return redirect('salon:select_date_time')

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time = datetime.strptime(time_str, '%H:%M').time()
        start_time = timezone.make_aware(datetime.combine(date, time))
        # print(f"time: {start_time}") # output -> "time: 2025-05-22 08:00:00+03:30"

    except ValueError:
        return redirect('salon:select_date_time')

    total_duration = services.aggregate(total=Sum('duration'))['total']
    total_price = services.aggregate(total=Sum('price'))['total']
    end_time = start_time + timedelta(minutes=total_duration)

    if request.method == 'POST':
        appointment = Appointment(
            customer=request.user,
            shop=shop,
            barber=barber,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        # print(f"start: {start_time}, end: {end_time}") #output -> "start: 2025-05-22 08:00:00+03:30, end: 2025-05-22 09:00:00+03:30"
        appointment.save()
        for service in services:
            AppointmentService.objects.create(appointment=appointment, service=service)
        del request.session['appointment_data']
        return redirect('salon:customer_appointments')

    return render(request, 'salon/confirm_appointment.html', {
        'shop': shop,
        'barber': barber,
        'services': services,
        'start_time': start_time,
        'end_time': end_time,
        'total_price': total_price,
        'total_duration': total_duration,
    })



# صفحه مشخصات آرایشگاه برای مشتری
@login_required
def shop_detail(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    shop_customer = get_object_or_404(CustomerShop, customer_id=5, shop_id=shop_id)
    # چک کردن عضویت مشتری
    # if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        return redirect('account:customer_profile')
    print(f"SHOP= {shop.customer_memberships}")
    # گرفتن آرایشگرهای آرایشگاه
    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)

    return render(request, 'salon/shop_detail.html', {
        'shop_customer': shop_customer,
        'barbers': barbers,
    })
