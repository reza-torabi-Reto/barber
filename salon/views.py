from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum, Case, When, Value, IntegerField
from datetime import datetime, timedelta, timezone
from django.utils import timezone
from django.utils.timezone import localtime
from django.contrib import messages
from django.utils.timesince import timesince
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from django.db.models import Q
import json
import jdatetime
from extensions.utils import j_convert_appoiment
from account.models import CustomUser, BarberProfile
from account.forms import BarberSignUpForm
from .utils.decorators import role_required
from .utils.appointment_utils  import get_total_service_duration, find_available_time_slots, message_nitif, jalali_str_to_gregorian_date
from .forms import ShopForm, ServiceForm, ShopScheduleFormSet, AppointmentService, ShopEditForm, BarberScheduleFormSet
from .models import Shop, BarberSchedule,Service, CustomerShop, ShopSchedule, Appointment, Notification


# ================ Manager Section ================
# صفحه ایجاد آرایشگاه توسط مدیر

@login_required
@role_required(['manager'])
def create_shop(request):
    if request.method == 'POST':
        form = ShopForm(request.POST)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.manager = request.user
            shop.save()
            return redirect('salon:manage_shop', shop_id=shop.id)
    else:
        form = ShopForm()
    print(f" -- {form}")
    return render(request, 'salon/create_shop.html', {'form': form})

# صفحه اطلاعات آرایشگاه برای مدیر
@login_required
@role_required(['manager'])
def manage_shop(request, shop_id):
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barbers = CustomUser.objects.filter(barber_profile__shop=shop)
    active_barbers = BarberProfile.objects.active().filter(shop=shop)

    services = Service.objects.filter(shop=shop)

    base_qs = Appointment.objects.filter(shop=shop)
    all_appointment_count = base_qs.filter().count()
    pending_appointment_count = base_qs.filter(status='pending').count()
    today_appointment_count = base_qs.filter(start_time__date=timezone.now().date()).count()
    return render(request, 'salon/manage_shop.html', {
        'shop': shop,
        'barbers': barbers,
        'active_barbers':active_barbers,
        'services': services,
        'all_appointment_count':all_appointment_count,
        'pending_appointment_count': pending_appointment_count,
        'today_appointment_count': today_appointment_count,
    })

# ویرایش آرایشگاه توسط مدیر
@login_required
@role_required(['manager'])
def edit_shop(request, shop_id):
    
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
@role_required(['manager'])
def manage_schedule(request, shop_id):
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
    form_schedule_pairs = sorted(
        form_schedule_pairs, 
        key=lambda x: desired_order[x[1].day_of_week])
    
    return render(request, 'salon/manage_schedule.html', {
        'shop': shop,
        'formset': formset,
        'form_schedule_pairs': form_schedule_pairs,
    })




@login_required
@role_required(['manager'])
def manage_barber_schedule(request, shop_id):
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    # barbers = BarberProfile.objects.filter(shop=shop)
    active_barbers = BarberProfile.objects.active().filter(shop=shop)
    selected_barber_id = request.GET.get('barber')

    if not selected_barber_id:
        return render(request, 'salon/manage_barber_schedule.html', {
            'shop': shop,
            'barbers': active_barbers,
            'selected_barber': None
        })

    selected_barber = get_object_or_404(BarberProfile, id=selected_barber_id, shop=shop)

    days = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']

    for day in days:
        BarberSchedule.objects.get_or_create(
            shop=shop,
            barber=selected_barber,
            day_of_week=day,
            defaults={'is_open': False}
        )

    # استفاده از Case برای ترتیب صحیح در queryset
    whens = [When(day_of_week=day, then=Value(index)) for index, day in enumerate(days)]

    schedules = BarberSchedule.objects.filter(shop=shop, barber=selected_barber).annotate(
        sort_order=Case(*whens, output_field=IntegerField())
    ).order_by('sort_order')

    formset = BarberScheduleFormSet(request.POST or None, queryset=schedules)

    if request.method == 'POST' and formset.is_valid():
        formset.save()
        return redirect('salon:manage_shop', shop_id=shop.id)
        # return redirect(f"{request.path}?barber={selected_barber.id}")

    form_schedule_pairs = list(zip(formset.forms, schedules))

    return render(request, 'salon/manage_barber_schedule.html', {
        'shop': shop,
        'barbers': active_barbers,
        'selected_barber': selected_barber,
        'formset': formset,
        'form_schedule_pairs': form_schedule_pairs,
    })


# حذف آرایشگر از آرایشگاه توسط مدیر
@login_required
@role_required(['manager'])
def delete_barber(request, shop_id, barber_id):
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barber = get_object_or_404(CustomUser, id=barber_id, barber_profile__shop=shop)
    barber.barber_profile.shop = None
    barber.barber_profile.save()
    return redirect('salon:manage_shop', shop_id=shop.id)

# ایجاد خدمت توسط مدیر
@login_required
@role_required(['manager'])
def create_service(request, shop_id):
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    # بررسی وجود آرایشگر
    has_barbers = BarberProfile.objects.filter(shop=shop, status=True, user__must_change_password= False).exists()
    
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
@role_required(['manager'])
def edit_service(request, shop_id, service_id):
    
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
@role_required(['manager'])
def delete_service(request, shop_id, service_id):
    
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)
    service.delete()
    return redirect('salon:manage_shop', shop_id=shop.id)

# نمایش نوبت ها برای مدیر

@login_required
@role_required(['manager'])
def manager_appointments(request, shop_id):
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
        'appointments': appointments,
        'pending_count':base_qs.filter(shop=shop, status='pending').order_by('-start_time').count(),
        'today_count':base_qs.filter(shop=shop, start_time__date=timezone.now().date()).order_by('-start_time').count(),
        'all_count':base_qs.filter(shop=shop).order_by('-start_time').count(),
        'now': timezone.now(),
    })



@login_required
@role_required(['manager'])
def manager_appointments(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    base_qs = Appointment.objects.filter(shop=shop)
    today = timezone.now().date()
    pending_only = request.GET.get('pending')

    # فیلتر نمایش اصلی
    if pending_only == '1':
        appointments = base_qs.filter(status='pending')
    elif pending_only == '2':
        appointments = base_qs.filter(start_time__date=today)
    else:
        appointments = base_qs

    appointments = appointments.select_related('barber', 'customer').order_by('-start_time')

    # شمارنده‌ها (همیشه لازمند برای نمایش در UI)
    counts = {
        'pending_count': base_qs.filter(status='pending').count(),
        'today_count': base_qs.filter(start_time__date=today).count(),
        'all_count': base_qs.count(),
    }

    return render(request, 'salon/manager_appointments.html', {
        'shop': shop,
        'appointments': appointments,
        **counts,
        'now': timezone.now(),
    })


@login_required
@role_required(['manager'])
def manager_appointments_days(request, shop_id):
 
    j_date_str = request.GET.get('date')
    status_filter = request.GET.get('status')

    today = datetime.today().date()
    if j_date_str:
        try:
            selected_date = jdatetime.date(*map(int, j_date_str.split('-'))).togregorian()
        except:
            selected_date = today
    else:
        selected_date = today

    start_of_day = datetime.combine(selected_date, datetime.min.time())
    end_of_day = datetime.combine(selected_date, datetime.max.time())

    # آرایشگرهای این فروشگاه
    barbers_in_shop = BarberProfile.objects.filter(shop_id=shop_id).values_list('user_id', flat=True)

    appointments = Appointment.objects.filter(
        start_time__range=(start_of_day, end_of_day),
        barber_id__in=barbers_in_shop,
    ).select_related('barber', 'customer')

    if status_filter in ['pending', 'confirmed', 'completed', 'canceled']:
        appointments = appointments.filter(status=status_filter)

    previous_day = selected_date - timedelta(days=1)
    next_day = selected_date + timedelta(days=1)

    context = {
        'appointments': appointments.order_by('start_time'),
        'shop_id': shop_id,
        'selected_date': jdatetime.date.fromgregorian(date=selected_date).strftime('%Y-%m-%d'),
        'previous_date': jdatetime.date.fromgregorian(date=previous_day).strftime('%Y-%m-%d'),
        'next_date': jdatetime.date.fromgregorian(date=next_day).strftime('%Y-%m-%d'),
        'status_filter': status_filter,
        'now': timezone.now(),

    }

    return render(request, 'salon/manager_appointments_days.html', context)


# تایید یک نوبت توسط مدیر
@login_required
@role_required(['manager'])
def appointment_detail_manager(request, id):
    
    appointment = get_object_or_404(Appointment, id=id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if appointment.status == 'canceled':
            messages.warning(request, 'این نوبت قبلاً لغو شده است.')
        else:
            if action == 'confirm':
                appointment.status = 'confirmed'
                appointment.save()
                msg_type = 'mo'
                messages.success(request, 'نوبت با موفقیت تایید شد.')
            elif action == 'cancel':
                appointment.status = 'canceled'
                appointment.canceled_by = 'manager'
                appointment.save()
                msg_type = 'mc'
                messages.success(request, 'نوبت لغو شد.')
            url = reverse('salon:appointment_detail_customer', args=[appointment.id])    
            # اعلان به مشتری
            message = message_nitif(appointment, appointment.start_time, msg_type)
            Notification.objects.create(
                user=appointment.customer,
                message=message,
                appointment=appointment,
                url=url,
                type='appointment_update'
            )
        return redirect(reverse('salon:manager_appointments', args=[appointment.shop.id]))


    return render(request, 'salon/appointment_detail_manager.html', {'appointment': appointment, 'now': timezone.now(),})


@login_required
@role_required(['barber'])
def appointment_detail_barber(request, id):
    
    appointment = get_object_or_404(Appointment, id=id)

    # if request.method == 'POST':
    #     action = request.POST.get('action')
    #     if appointment.status == 'canceled':
    #         messages.warning(request, 'این نوبت قبلاً لغو شده است.')
    #     else:
    #         if action == 'confirm':
    #             appointment.status = 'confirmed'
    #             appointment.save()
    #             msg_type = 'mo'
    #             messages.success(request, 'نوبت با موفقیت تایید شد.')
    #         elif action == 'cancel':
    #             appointment.status = 'canceled'
    #             appointment.canceled_by = 'manager'
    #             appointment.save()
    #             msg_type = 'mc'
    #             messages.success(request, 'نوبت لغو شد.')
    #         url = reverse('salon:appointment_detail_customer', args=[appointment.id])    
    #         # اعلان به مشتری
    #         message = message_nitif(appointment, appointment.start_time, msg_type)
    #         Notification.objects.create(
    #             user=appointment.customer,
    #             message=message,
    #             appointment=appointment,
    #             url=url,
    #             type='appointment_update'
    #         )
        # return redirect(reverse('salon:manager_appointments', args=[appointment.shop.id]))


    return render(request, 'salon/appointment_detail_barber.html', {'appointment': appointment, 'now': timezone.now(),})


@login_required
@role_required(['manager'])
def complete_appointment_confirm(request, id):
    
    appointment = get_object_or_404(Appointment, id=id)

    # بررسی وضعیت و زمان نوبت
    if appointment.status != 'confirmed':
        messages.error(request, 'فقط نوبت‌های تأییدشده قابل تکمیل هستند.')
        return redirect('salon:manager_appointments', appointment.shop.id)

    if appointment.end_time > now():
        messages.error(request, 'هنوز زمان این نوبت به پایان نرسیده است.')
        return redirect('salon:manager_appointments', appointment.shop.id)

    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()

        # اعلان برای مشتری
        # msg_type = 'cp'
        # message = message_nitif(appointment, appointment.start_time, msg_type)
        # Notification.objects.create(
        #     user=appointment.customer,
        #     message=message,
        #     appointment=appointment,
        #     type='appointment_completed',
        #     url='',  # در صورت نیاز لینک به صفحه جزییات نوبت قرار بده
        # )

        messages.success(request, 'نوبت با موفقیت به عنوان تکمیل‌شده ثبت شد.')
        return redirect('salon:manager_appointments', appointment.shop.id)

    return render(request, 'salon/complete_appointment_confirm.html', {'appointment': appointment})

@login_required
@role_required(['barber'])
def barber_appointments(request, shop_id):
    
    # بررسی اینکه این آرایشگر در این فروشگاه فعال هست یا نه
    barber_profile = get_object_or_404(BarberProfile, user=request.user, shop__id=shop_id)
    shop = barber_profile.shop
    base_qs = Appointment.objects.filter(shop=shop, barber=request.user)
    pending_only = request.GET.get('pending') 

    if pending_only == '1':
        appointments = base_qs.filter(status='pending').order_by('-start_time')
    elif pending_only == '2':
        appointments = base_qs.filter(start_time__date=timezone.now().date()).order_by('-start_time')
    else:
        appointments = base_qs.order_by('-start_time')
    
    return render(request, 'salon/barber_appointments.html', {
        'shop': shop,
        'barber_profile': barber_profile,
        'appointments': appointments,
        'now': timezone.now(),
    })

@login_required
@role_required(['customer'])
def appointment_detail_customer(request, id):
    
    appointment = get_object_or_404(Appointment, id=id, customer=request.user)

    if request.method == 'POST':
        if appointment.status == 'canceled':
            messages.warning(request, 'این نوبت قبلاً لغو شده است.')
        elif appointment.status in ['pending', 'confirmed']:
            appointment.status = 'canceled'
            appointment.canceled_by = 'customer'
            appointment.save()
            messages.success(request, 'نوبت با موفقیت لغو شد.')

            # ارسال اعلان به مدیر سالن
            url = reverse('salon:appointment_detail_customer', args=[appointment.id])
            message = message_nitif(appointment, appointment.start_time, 'cc')  # cc = cancel by customer
            Notification.objects.create(
                user=appointment.shop.manager,
                message=message,
                appointment=appointment,
                url=url,
                type='appointment_canceled',
            )

        return redirect('salon:customer_appointments')  # صفحه لیست نوبت‌ها

    return render(request, 'salon/appointment_detail_customer.html', {'appointment': appointment, 'now': timezone.now(),})

# ================ Customer Section ================
# صفحه تایید نوبت توسط مشتری
@login_required
@role_required(['customer'])
def confirm_appointment(request):
    appointment_data = request.session.get('appointment_data')
    if not appointment_data:
        return redirect('account:customer_profile')

    shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
    services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
    # barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)
    barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], barber_profile__shop=shop)
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
        message_type = 'co'
        url = reverse('salon:appointment_detail_manager', args=[appointment.id])    
        message = message_nitif(appointment, start_time, message_type)
        Notification.objects.create(
                            user=shop.manager,  # کاربری که نوبت بهش تعلق داره
                            message=message,
                            appointment=appointment,
                            url=url,
                            type='appointment_confirmed',
                                )   
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
#نمایش نوبت ها برای مشتری
@login_required
@role_required(['customer'])
def customer_appointments(request):
    
    appointments = Appointment.objects.filter(customer=request.user).order_by('-start_time')
    return render(request, 'salon/customer_appointments.html', {'appointments': appointments, 'now': timezone.now(),})

@login_required
@role_required(['customer'])
def shop_customer_appointments(request, shop_id):
    
    appointments = Appointment.objects.filter(customer=request.user, shop_id=shop_id).order_by('-start_time')
    
    return render(request, 'salon/customer_appointments.html', {'appointments': appointments})


# صفحه انتخاب آرایشگر و خدمات توسط مشتری
@login_required
@role_required(['customer'])
def book_appointment(request, shop_id):
    
    # بررسی عضویت مشتری در آرایشگاه
    shop = get_object_or_404(Shop, id=shop_id)
    if not CustomerShop.objects.filter(customer=request.user, shop=shop, is_active=True).exists():
        return redirect('account:customer_profile')

    # دریافت آرایشگران فعال آرایشگاه
    # barbers = CustomUser.objects.filter(role='barber',barber_profile__shop=shop,barber_profile__status=True).prefetch_related(
    #     'barber_profile', 'barber_profile__services')
    barbers = CustomUser.objects.filter(barber_profile__shop=shop,barber_profile__status=True).prefetch_related(
        'barber_profile', 'barber_profile__services')
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
        barber = get_object_or_404(CustomUser, id=barber_id, barber_profile__shop=shop)
        print("1++")
        services = Service.objects.filter(id__in=service_ids, shop=shop, barber=barber.barber_profile)
        print("2++")
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
        # return redirect('salon:select_date_time')
        return redirect('salon:select_date_time_barber')

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
# @login_required
# @role_required(['customer'])
# def select_date_time(request):
    
#     appointment_data = request.session.get('appointment_data')
#     if not appointment_data:
#         return redirect('account:customer_profile')

#     shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
#     services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
#     barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)

#     total_duration = get_total_service_duration(services)
#     if total_duration == 0:
#         return render(request, 'salon/select_date_time.html', {
#             'shop': shop,
#             'services': services,
#             'barber': barber,
#             'dates': [],
#             'appointment_data': appointment_data,
#             'total_duration': total_duration,
#             'error': 'مدت زمان سرویس‌ها معتبر نیست.'
#         })

#     schedules = ShopSchedule.objects.filter(shop=shop, is_open=True)
#     working_days = {s.day_of_week: s for s in schedules}
    
#     today = timezone.now().date()
#     jalali_dates = []

#     for i in range(30):
#         date = today + timedelta(days=i)
#         day_of_week = date.strftime('%A').lower()
#         schedule = working_days.get(day_of_week)
#         if not schedule or not schedule.start_time or not schedule.end_time:
#             continue

#         available_times = find_available_time_slots(date, schedule, barber, total_duration)
#         if available_times:
#             jalali_dates.append({
#                 'gregorian_date': date,
#                 'jalali_date': j_convert_appoiment(date),
#                 'day_of_week': schedule.get_day_of_week_display(),
#             })

#     return render(request, 'salon/select_date_time.html', {
#         'shop': shop,
#         'barber': barber,
#         'services': services,
#         'total_duration': total_duration,
#         'dates': jalali_dates,
#         'appointment_data': appointment_data,
#         'error': 'هیچ روز آزادی برای رزرو در ۸ روز آینده در دسترس نیست.' if not jalali_dates else None,
#     })


@login_required
@role_required(['customer'])
def select_date_time_barber(request):
    print("SELECT DATE BARBER")    
    appointment_data = request.session.get('appointment_data')
    if not appointment_data:
        return redirect('account:customer_profile')

    shop = get_object_or_404(Shop, id=appointment_data['shop_id'])
    services = Service.objects.filter(id__in=appointment_data['services'], shop=shop)
    # barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], role='barber', barber_profile__shop=shop)
    barber = get_object_or_404(CustomUser, id=appointment_data['barber_id'], barber_profile__shop=shop)
    total_duration = get_total_service_duration(services)
    if total_duration == 0:
        return render(request, 'salon/select_date_time_barber.html', {
            'shop': shop,
            'services': services,
            'barber': barber,
            'dates': [],
            'appointment_data': appointment_data,
            'total_duration': total_duration,
            'error': 'مدت زمان سرویس‌ها معتبر نیست.'
        })
    
    schedules = BarberSchedule.objects.filter(shop=shop,barber= barber.barber_profile ,is_open=True)
    
    working_days = {s.day_of_week: s for s in schedules}
    today = timezone.now().date()
    jalali_dates = []

    for i in range(30):
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
        
    return render(request, 'salon/select_date_time_barber.html', {
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
@role_required(['customer'])
def get_available_times(request):
    
    # اشکال لود نشدن زمان آزاد
    shop_id = request.GET.get('shop_id')
    barber_id = request.GET.get('barber_id')
    date_str = request.GET.get('date')
    service_ids = request.GET.getlist('services')

    if not (shop_id and barber_id and date_str and service_ids):
        return JsonResponse({'times': []}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # barber = CustomUser.objects.get(id=barber_id, role='barber', barber_profile__shop_id=shop_id)
        barber = CustomUser.objects.get(id=barber_id, barber_profile__shop_id=shop_id)
        services = Service.objects.filter(id__in=service_ids, shop_id=shop_id)
        total_duration = get_total_service_duration(services)
    except Exception:
        return JsonResponse({'times': []}, status=400)


    if total_duration == 0:
        return JsonResponse({'times': []}, status=400)

    day_of_week = selected_date.strftime('%A').lower()
    try:
        schedule = BarberSchedule.objects.get(shop_id=shop_id,barber=barber.barber_profile ,day_of_week=day_of_week, is_open=True)
    except BarberSchedule.DoesNotExist:
        print("Times***")
        return JsonResponse({'times': []})

    available_times = find_available_time_slots(selected_date, schedule, barber, total_duration)
    return JsonResponse({'times': available_times})


# صفحه مشخصات آرایشگاه برای مشتری
@login_required
@role_required(['customer'])
def shop_detail(request, shop_id):

    shop = get_object_or_404(Shop, id=shop_id)    
    if not CustomerShop.objects.filter(customer=request.user, shop=shop).exists():
        return redirect('account:customer_profile')
    
    shop_customer = get_object_or_404(CustomerShop, customer_id=request.user, shop_id=shop_id)
    
    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)

    return render(request, 'salon/shop_detail.html', {
        'shop_customer': shop_customer,
        'barbers': barbers,
    })


@login_required
def get_unread_notifications(request):
    notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')
    data = []
    for noti in notifications:
        data.append({
            'id': noti.id,
            'message': noti.message,
            'created_at': timesince(noti.created_at) + ' پیش',
            'url': noti.url if noti.url else '',
        })

    return JsonResponse({'notifications': data})


@login_required
@require_POST
def mark_as_read(request):
    try:
        data = json.loads(request.body)
        notif_id = data.get('id')
        notification = get_object_or_404(Notification, id=notif_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)