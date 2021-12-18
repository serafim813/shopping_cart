from rest_framework import viewsets
from rest_framework.decorators import action
from .models import User, Cart
from .serializers import UserSerializer, CartSerializer
from .helpers import ReportHelper
from django.http.response import JsonResponse

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer



class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().order_by('id')
    serializer_class = CartSerializer


    @action(methods=['get'], detail=False, url_path='checkout/(?P<userId>[^/.]+)', url_name='checkout')
    def checkout(self, request, *args, **kwargs):
        ReportHelper.get_daily_orders(self)
        return(JsonResponse(1, safe=False))
