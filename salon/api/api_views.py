from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from salon.models import Shop
from salon.api.serializers import ShopCreateSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_shop(request):
    if request.user.role != 'manager':
        return Response({'detail': 'Only managers can create shops.'}, status=403)

    serializer = ShopCreateSerializer(data=request.data)
    if serializer.is_valid():
        shop = serializer.save(manager=request.user)
        return Response(ShopCreateSerializer(shop).data, status=201)
    return Response(serializer.errors, status=400)
