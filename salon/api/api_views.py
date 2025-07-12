from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from account.models import CustomUser
from salon.models import Shop, Service, Appointment
from salon.api.serializers import ShopCreateSerializer, ShopManageSerializer, ShopEditSerializer, BarberCreateSerializer, ServiceSerializer


# create shop
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_shop(request):
    if request.user.role != 'manager':
        return Response({'detail': 'Only managers can create shops.'}, status=403)

    serializer = ShopCreateSerializer(data=request.data)
    if serializer.is_valid():
        shop = serializer.save(manager=request.user)
        return Response(ShopCreateSerializer(shop).data, status=201)
    return Response(serializer.errors, status=400)

# manage shop
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_manage_shop(request, shop_id):
    user = request.user
    if user.role != 'manager':
        return Response({'detail': 'Unauthorized'}, status=403)

    shop = get_object_or_404(Shop, id=shop_id, manager=user)

    barbers = CustomUser.objects.filter(role='barber', barber_profile__shop=shop)
    services = Service.objects.filter(shop=shop)
    appointments = Appointment.objects.filter(shop=shop)

    data = {
        'shop': shop,
        'barbers': barbers,
        'services': services,
        'appointments': {
            'all': appointments.count(),
            'pending': appointments.filter(status='pending').count(),
            'today': appointments.filter(start_time__date=timezone.now().date()).count(),
        }
    }

    serializer = ShopManageSerializer(data)
    return Response(serializer.data)

# edit shop
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def api_edit_shop(request, shop_id):
    try:
        shop = Shop.objects.get(id=shop_id, manager=request.user)
    except Shop.DoesNotExist:
        return Response({'error': 'آرایشگاه پیدا نشد یا شما مدیر آن نیستید.'}, status=404)

    if request.method == 'GET':
        serializer = ShopEditSerializer(shop)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = ShopEditSerializer(shop, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

# create barber
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_barber(request, shop_id):
    if request.user.role != 'manager':
        return Response({'detail': 'دسترسی غیرمجاز'}, status=403)

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)

    serializer = BarberCreateSerializer(data=request.data, context={'shop': shop})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

# delete barber
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_barber(request, shop_id, barber_id):
    if request.user.role != 'manager':
        return Response({'detail': 'دسترسی غیرمجاز'}, status=403)

    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    barber = get_object_or_404(CustomUser, id=barber_id, role='barber', barber_profile__shop=shop)

    # حذف ارتباط با آرایشگاه
    barber.barber_profile.shop = None
    barber.barber_profile.save()

    return Response({'detail': 'آرایشگر از فروشگاه حذف شد.'}, status=204)


# create service
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_service(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)

    serializer = ServiceSerializer(data=request.data, context={'shop': shop})
    if serializer.is_valid():
        service = serializer.save(shop=shop)
        return Response(ServiceSerializer(service).data, status=201)
    return Response(serializer.errors, status=400)

# edit service
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def api_edit_service(request, shop_id, service_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)

    partial = request.method == 'PATCH'
    serializer = ServiceSerializer(service, data=request.data, partial=partial, context={'shop': shop})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

# delete service
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_service(request, shop_id, service_id):
    shop = get_object_or_404(Shop, id=shop_id, manager=request.user)
    service = get_object_or_404(Service, id=service_id, shop=shop)
    service.delete()
    return Response({'detail': 'خدمت حذف شد.'}, status=204)
