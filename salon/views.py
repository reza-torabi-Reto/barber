from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum
from django.utils import timezone
from extensions.utils import j_convert_appoiment
import jdatetime  
from django.contrib import messages
from .forms import ShopForm, ServiceForm, ServiceEditForm, ShopScheduleFormSet, AppointmentForm,AppointmentService, ShopEditForm
from .models import Shop, Service, CustomerShop, ShopSchedule, Appointment
from account.models import CustomUser, BarberProfile
from account.forms import BarberSignUpForm

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
    for b in barbers:
        print(f'Status = {b.barber_profile.status}')
    return render(request, 'salon/manage_shop.html', {
        'shop': shop,
        'barbers': barbers,
        'services': services,
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

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    if request.method == 'POST':
        form = BarberSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            barber = form.save(shop=shop)
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = BarberSignUpForm()
        print("Fields in form:", form.fields.keys())

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
    if request.method == 'POST':
        form = ServiceForm(request.POST, shop=shop)
        if form.is_valid():
            service = form.save(commit=False)   # آرایشگر انتخاب نمیشه
            service.shop = shop
            service.barber = form.cleaned_data['barber']
            service.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ServiceForm(shop=shop)
    return render(request, 'salon/create_service.html', {'form': form, 'shop': shop})

# ویرایش خدمت توسط مدیر
@login_required
def edit_service(request, shop_id, service_id):
    if request.user.role != 'manager':
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)

    if request.method == 'POST':
        form = ServiceEditForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ServiceEditForm(instance=service)

    return render(request, 'salon/edit_service.html', {'form': form, 'shop': shop, 'service': service})

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
    appointments = Appointment.objects.filter(shop=shop).order_by('-start_time') 
    
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
            return render(request, 'salon/book_appointment.html', {
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
# def book_appointment(request, shop_id):
#     shop = get_object_or_404(Shop, id=shop_id)

#     if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
#         return redirect('account:customer_profile')

#     if request.method == 'POST':
#         form = AppointmentForm(request.POST, customer=request.user, shop=shop)
#         if form.is_valid():
#             # گرفتن اطلاعات از فرم
#             barber_id = form.cleaned_data['barber'].id
#             print(f'BARBER_ID: {barber_id}')

#             service_ids = [str(service.id) for service in form.cleaned_data['services']]

#             # ریدایرکت به view بعدی همراه با پارامترها
#             return redirect('salon:select_date_time', shop_id=shop.id, barber_id=barber_id, service_ids=",".join(service_ids))
#     else:
#         form = AppointmentForm(customer=request.user, shop=shop)

#     # ساخت دیکشنری خدمات برای هر آرایشگر
#     barber_services = defaultdict(list)
#     services = Service.objects.filter(
#         shop=shop,
#         barber__status=True,
#         barber__shop=shop
#     ).select_related('barber__user')

#     for service in services:
#         user = service.barber.user
#         barber_services[user].append(service)

#     context = {
#         'form': form,
#         'shop': shop,
#         'barber_services': dict(barber_services),
#     }
#     return render(request, 'salon/book_appointment.html', context)

# @login_required
# def book_appointment(request, shop_id):
#     shop = get_object_or_404(Shop, id=shop_id)
#     if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
#         return redirect('account:customer_profile')

#     if request.method == 'POST':
#         form = AppointmentForm(request.POST, customer=request.user, shop=shop)
#         print("POST data:", request.POST)
#         if form.is_valid():
#             print("Cleaned data:", form.cleaned_data)
#             # ذخیره اطلاعات موقت در session
#             request.session['appointment_data'] = {
#                 'shop_id': shop_id,
#                 'services': [str(service.id) for service in form.cleaned_data['services']],
#                 'barber_id': str(form.cleaned_data['barber'].id),
#             }
#             return redirect('salon:select_date_time')
#         else:
#             print("Form errors:", form.errors)
#     else:
#         form = AppointmentForm(customer=request.user, shop=shop)
#     return render(request, 'salon/book_appointment.html', {
#         'form': form,
#         'shop': shop,
#     })

# گرفتن اطلاعات سرویس‌ها در صفحه book_appointment
def get_shop_details(request):
    shop_id = request.GET.get('shop_id')
    if not shop_id:
        return JsonResponse({'services': [], 'barbers': []})

    services = Service.objects.filter(shop_id=shop_id).values('id', 'name', 'price', 'duration')
    barbers = CustomUser.objects.filter(role='barber',barber_profile__shop_id=shop_id).values('id', 'username')

    return JsonResponse({
        'services': list(services),
        'barbers': list(barbers),
    })

# صفحه تعیین روز/ساعت نوبت توسط مشتری
def select_date_time(request):
    appointment_data = request.session.get('appointment_data')
    if not appointment_data:
        return redirect('account:customer_profile')

    shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
    services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
    barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)
    total_duration = services.aggregate(total=Sum('duration'))['total'] or 0
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
    working_days = [schedule.day_of_week for schedule in schedules]

    if not working_days:
        return render(request, 'salon/select_date_time.html', {
            'shop': shop,
            'services': services,
            'barber': barber,
            'dates': [],
            'appointment_data': appointment_data,
            'total_duration': total_duration,
            'error': 'هیچ روز کاری برای این آرایشگاه تعریف نشده است.'
        })

    today = timezone.now().date()
    dates = []
    schedule_dict = {s.day_of_week: s for s in schedules}
    jalali_dates = []

    for i in range(31):
        date = today + timedelta(days=i)
        day_of_week = date.strftime('%A').lower()
        if day_of_week not in working_days:
            # print(f"Skipping {date} - not in working days")
            continue

        schedule = schedule_dict.get(day_of_week)
        if not schedule or not schedule.start_time or not schedule.end_time:
            # print(f"Skipping {date} - no valid schedule")
            continue

        work_start = schedule.start_time
        work_end = schedule.end_time

        booked_slots = Appointment.objects.filter(
            barber=barber,
            start_time__date=date,
            status__in=['pending', 'confirmed']
        ).values('start_time', 'end_time')
        # print(f"Booked slots for {date}: {list(booked_slots)}")

        current_time = timezone.make_aware(datetime.combine(date, work_start))
        slot_end = timezone.make_aware(datetime.combine(date, work_end))
        slot_interval = timedelta(minutes=30)
        has_free_slot = False

        while current_time + timedelta(minutes=total_duration) <= slot_end:
            slot_end_time = current_time + timedelta(minutes=total_duration)
            is_available = True

            if schedule.break_start and schedule.break_end:
                break_start = timezone.make_aware(datetime.combine(date, schedule.break_start))
                break_end = timezone.make_aware(datetime.combine(date, schedule.break_end))
                if break_start <= current_time < break_end or break_start < slot_end <= break_end:
                    is_available = False

            for slot in booked_slots:
                booked_start = slot['start_time']
                booked_end = slot['end_time']
                if not (slot_end_time <= booked_start or current_time >= booked_end):
                    is_available = False
                    break

            if is_available:
                has_free_slot = True
                break

            current_time += slot_interval
        if has_free_slot:
            jalali_date_str = j_convert_appoiment(date)
            print(f'DATE===:{jalali_date_str}=======')

            jalali_dates.append({
                'gregorian_date': date,
                'jalali_date': jalali_date_str,  # مثلاً "7 اردیبهشت 1404"
                'day_of_week': schedule.get_day_of_week_display(),
            })

    return render(request, 'salon/select_date_time.html', {
        'shop': shop,
        'services': services,
        'barber': barber,
        'dates': jalali_dates,
        'appointment_data': appointment_data,
        'total_duration': total_duration,
        'error': 'هیچ روز آزادی برای رزرو در ۳۰ روز آینده در دسترس نیست.' if not jalali_dates else None,
    })

# نمایش ساعت های خالی روزهای هفته در صفحه:(select_date_time) 
def get_available_times(request):
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
        total_duration = services.aggregate(total=Sum('duration'))['total'] or 0
    except (ValueError, CustomUser.DoesNotExist, Service.DoesNotExist):
        return JsonResponse({'times': []}, status=400)

    if total_duration == 0:
        return JsonResponse({'times': []}, status=400)

    shop = Shop.objects.get(id=shop_id)
    day_of_week = selected_date.strftime('%A').lower()

    try:
        schedule = ShopSchedule.objects.get(shop=shop, day_of_week=day_of_week, is_open=True)
    except ShopSchedule.DoesNotExist:
        return JsonResponse({'times': []})

    if not schedule.start_time or not schedule.end_time:
        return JsonResponse({'times': []})

    work_start = schedule.start_time
    work_end = schedule.end_time
    break_start = schedule.break_start
    break_end = schedule.break_end

    work_start = timezone.make_aware(datetime.combine(selected_date, work_start))
    work_end = timezone.make_aware(datetime.combine(selected_date, work_end))
    if break_start and break_end:
        break_start = timezone.make_aware(datetime.combine(selected_date, break_start))
        break_end = timezone.make_aware(datetime.combine(selected_date, break_end))

    booked_slots = Appointment.objects.filter(
        barber_id=barber_id,
        start_time__date=selected_date,
        status__in=['pending', 'confirmed']
    ).values('start_time', 'end_time')

    available_times = []
    current_time = work_start
    slot_interval = timedelta(minutes=30)

    while current_time + timedelta(minutes=total_duration) <= work_end:
        slot_end = current_time + timedelta(minutes=total_duration)
        is_available = True

        if break_start and break_end:
            if break_start <= current_time < break_end or break_start < slot_end <= break_end:
                is_available = False

        for slot in booked_slots:
            booked_start = slot['start_time']
            booked_end = slot['end_time']
            if not (slot_end <= booked_start or current_time >= booked_end):
                is_available = False
                break

        if is_available:
            available_times.append({
                'start_time': current_time.strftime('%H:%M'),
                'end_time': slot_end.strftime('%H:%M')
            })

        current_time += slot_interval

    jalali_date = jdatetime.date.fromgregorian(date=selected_date)
    print(f"Available times for {date_str} ({jalali_date}): {available_times}")

    return JsonResponse({'times': available_times})

# صفحه تایید نوبت توسط مشتری
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
