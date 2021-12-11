from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Cart
from .serializers import UserSerializer, CartSerializer
from .helpers import CartHelper
from django.http.response import JsonResponse
from shopping_cart_api.products.models import Category, Product
from shopping_cart_api.discounts.models import Campaign
from django.db.models import Count
import csv
import copy
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer



class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().order_by('id')
    serializer_class = CartSerializer


    @action(methods=['get'], detail=False, url_path='checkout/(?P<userId>[^/.]+)', url_name='checkout')
    def checkout(self, request, *args, **kwargs):
        checkout_details1 = []

        l = []
        k = []
        t = Cart.objects.extra({'created_at':"date(created_at)"}).values('created_at').annotate(day_total=Count('id'))
        for i in range(len(t)):
            k.append(t[i]['created_at'])
        for j in range(len(k)):
            l.append([])

        #получение информации о покупках
        for j in range(len(k)):
            w = []
            m = Cart.objects.filter(created_at__range=[k[j], k[j]])
            for i in range(len(m)):
                w.append(m[i].id)
            for i in w:
                id = Cart.objects.filter(id=i)
                cart_helper = CartHelper(id)
                checkout_details = cart_helper.prepare_cart_for_checkout()

                if type(checkout_details) != bool:
                    l[j].append(checkout_details['products'][0])
                    checkout_details1.append(checkout_details['products'][0])
        d = []
        for i in range(len(Campaign.objects.all())):
            d.append({})
            p = d[i]
            y = Campaign.objects.all()[i].name
            k = Campaign.objects.all()[i].target_category.title
            o = Campaign.objects.all()[i].target_category_id
            p[y] = 0
            p[k] = 0
            for i in range(len(Product.objects.filter(category_id=o))):
                z = Product.objects.filter(category_id=o)[i].title
                p[z] = [0,0]
        a = d
        z1 = []
        for i in range(len(a)):
            z1.append({})

        def update():
            for i in range(len(a)):
                z1[i] = copy.deepcopy(a[i])
        update()

        # создание первого отчета
        with open("first_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            update()
            k = []
            for i in range(len(t)):
                k.append(t[i]['created_at'])
            for j in range(len(k)):

                file_writer.writerow([k[j]])
                for i in range(len(l[j])):
                    g = l[j]
                    d = 0
                    if g[i]['total_discount'] != 0:
                        d = g[i]['total_price'] / g[i]['total_discount']
                    file_writer.writerow([g[i]['updated_at'].strftime("%m.%d.%Y %H:%M"), g[i]['product_name'], g[i]['total_price'], g[i]['total_discount'], d])
        # создание второго отчета
        with open("second_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            update()
            o = []
            k = []
            for i in range(len(t)):
                k.append(t[i]['created_at'])
            for i in range(len(l)):
                update()
                o.append(k[i])

                for j in range(len(z1)):
                    r = cart_helper.creating_data_for_the_report(l[i], z1[j])
                    o.append(r)
            for r in o:
                if len(r) == 10:
                    file_writer.writerow([r])
                else:
                    u = list(r.keys())

                    file_writer.writerow([u[0],u[1],r[u[0]],r[u[1]]])
        # создание третьего отчета
        with open("third_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            update()
            o = []
            k = []
            for i in range(len(t)):
                k.append(t[i]['created_at'])
            for i in range(len(l)):
                update()
                o.append(k[i])

                for j in range(len(z1)):
                    r = cart_helper.creating_data_for_the_report(l[i], z1[j])
                    o.append(r)
            for r in o:
               if len(r) == 10:
                   file_writer.writerow([r])
               else:
                for i in range(len(r) - 2):
                    u = list(r.keys())
                    file_writer.writerow([u[0], u[2+i], r[u[2+i]][0], r[u[2+i]][1]])

        if not checkout_details:
            return Response(status=status.HTTP_404_NOT_FOUND,
                            data={'error': 'Cart of user is empty.'})


        return(JsonResponse(checkout_details1, safe=False))


