from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, timezone
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from .forms import ShopForm, ServiceForm, ShopScheduleFormSet, AppointmentForm
from .models import Shop, Service, CustomerShop, ShopSchedule, Appointment
from account.models import CustomUser
from account.forms import BarberSignUpForm

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

@login_required
def create_barber(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    if request.method == 'POST':
        form = BarberSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            barber = form.save(shop=shop)
            return redirect('salon:list_barber', shop_id=shop.id)
    else:
        form = BarberSignUpForm()
    return render(request, 'salon/create_barber.html', {'form': form, 'shop': shop})

@login_required
def list_barber(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)
    return render(request, 'salon/list_barber.html', {'shop': shop, 'barbers': barbers})

@login_required
def create_service(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.shop = shop
            service.save()
            return redirect('salon:service_list', shop_id=shop.id)
    else:
        form = ServiceForm()
    return render(request, 'salon/create_service.html', {'form': form, 'shop': shop})

@login_required
def service_list(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    services = Service.objects.filter(shop=shop)
    return render(request, 'salon/service_list.html', {'shop': shop, 'services': services})

@login_required
def manage_shop(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)
    services = Service.objects.filter(shop=shop)

    return render(request, 'salon/manage_shop.html', {
        'shop': shop,
        'barbers': barbers,
        'services': services,
    })

@login_required
def delete_barber(request, shop_id, barber_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barber = get_object_or_404(CustomUser, id=barber_id, role='barber', barber_profile__shop=shop)
    barber.barber_profile.shop = None
    barber.barber_profile.save()
    return redirect('salon:manage_shop', shop_id=shop.id)

@login_required
def delete_service(request, shop_id, service_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)
    service.delete()
    return redirect('salon:manage_shop', shop_id=shop.id)

@login_required
def edit_service(request, shop_id, service_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ServiceForm(instance=service)

    return render(request, 'salon/edit_service.html', {'form': form, 'shop': shop, 'service': service})

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


# salon/views.py
@login_required
def book_appointment(request, shop_id):
    if request.user.role != 'customer':
        return redirect('home')
    
    shop = get_object_or_404(Shop, id=shop_id)
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        return redirect('account:customer_profile')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, customer=request.user, shop=shop)
        print("POST data:", request.POST)
        if form.is_valid():
            print("Cleaned data:", form.cleaned_data)
            appointment = form.save()
            return redirect('salon:customer_appointments')
        else:
            print("Form errors:", form.errors)
    else:
        form = AppointmentForm(customer=request.user, shop=shop)

    return render(request, 'salon/book_appointment.html', {'form': form, 'shop': shop})


# salon/views.py
def get_shop_details(request):
    shop_id = request.GET.get('shop_id')
    if not shop_id:
        return JsonResponse({'services': [], 'barbers': []})

    services = Service.objects.filter(shop_id=shop_id).values('id', 'name', 'price', 'duration')
    barbers = CustomUser.objects.filter(
        role='barber',
        barber_profile__shop_id=shop_id
    ).values('id', 'username')

    return JsonResponse({
        'services': list(services),
        'barbers': list(barbers),
    })

@login_required
def customer_appointments(request):
    if request.user.role != 'customer':
        return redirect('home')

    appointments = Appointment.objects.filter(customer=request.user).order_by('-start_time')
    return render(request, 'salon/customer_appointments.html', {'appointments': appointments})

@login_required
def barber_appointments(request):
    if request.user.role != 'barber':
        return redirect('home')

    appointments = Appointment.objects.filter(barber=request.user).order_by('-start_time')
    return render(request, 'salon/barber_appointments.html', {'appointments': appointments})

@login_required
def manager_appointments(request, shop_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    appointments = Appointment.objects.filter(shop=shop).order_by('-start_time')
    return render(request, 'salon/manager_appointments.html', {
        'shop': shop,
        'appointments': appointments
    })


def get_available_times(request):
    shop_id = request.GET.get('shop_id')
    barber_id = request.GET.get('barber_id')
    date_str = request.GET.get('date')
    service_ids = request.GET.getlist('services')

    if not all([shop_id, barber_id, date_str, service_ids]):
        return JsonResponse({'times': []})

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'times': []})

    shop = get_object_or_404(Shop, id=shop_id)
    barber = get_object_or_404(CustomUser, id=barber_id, role='barber', barber_profile__shop=shop)
    services = Service.objects.filter(id__in=service_ids, shop=shop)

    if not services.exists():
        return JsonResponse({'times': []})

    # محاسبه مجموع مدت زمان
    total_duration = services.aggregate(total=Sum('duration'))['total']
    if not total_duration:
        return JsonResponse({'times': []})

    # گرفتن برنامه کاری
    day_of_week = selected_date.strftime('%A').lower()
    schedule = ShopSchedule.objects.filter(shop=shop, day_of_week=day_of_week).first()
    if not schedule or not schedule.is_open:
        return JsonResponse({'times': []})

    # محاسبه زمان‌های آزاد
    available_times = []
    start_time = datetime.combine(selected_date, schedule.start_time)
    end_time = datetime.combine(selected_date, schedule.end_time)
    break_start = datetime.combine(selected_date, schedule.break_start) if schedule.break_start else None
    break_end = datetime.combine(selected_date, schedule.break_end) if schedule.break_end else None

    start_time = timezone.make_aware(start_time)
    end_time = timezone.make_aware(end_time)
    if break_start:
        break_start = timezone.make_aware(break_start)
        break_end = timezone.make_aware(break_end)

    booked_appointments = Appointment.objects.filter(
        barber=barber,
        start_time__date=selected_date,
        status__in=['pending', 'confirmed']
    ).values('start_time', 'end_time')

    current_time = start_time
    while current_time + timedelta(minutes=total_duration) <= end_time:
        slot_end = current_time + timedelta(minutes=total_duration)
        is_available = True

        for appt in booked_appointments:
            appt_start = appt['start_time']
            appt_end = appt['end_time']
            if current_time < appt_end and slot_end > appt_start:
                is_available = False
                break

        if break_start and break_end:
            if current_time < break_end and slot_end > break_start:
                is_available = False

        if is_available:
            available_times.append(current_time.strftime('%H:%M'))

        current_time += timedelta(minutes=30)  # گام‌های 30 دقیقه‌ای

    return JsonResponse({'times': available_times})