from .models import Cart
import datetime
from shopping_cart_api.discounts.helpers import CampaignHelper

class CartHelper:

    def __init__(self, id):
        self.discount_type = []
        self.user = id[0].user
        self.id = id[0].id
        self.cart_base_total_amount = 0
        self.cart_final_total_amount = 0
        self.campaign_discount_amounts = []
        self.campaign_discount_amount = 0
        self.coupon_discount_amount = 0
        self.delivery_cost = 'Undiscounted'
        self.cart_items = []
        self.discounts = {}
        self.checkout_details = {'products': []}

    def prepare_cart_for_checkout(self):
        self.cart_items = Cart.objects.filter(id=self.id)

        if not self.cart_items:
            return False

        self.calculate_cart_base_total_amount()
        self.get_campaign_discounts()
        self.calculate_discount_amounts()
        self.get_total_amount_after_discounts()
        self.prepare_checkout_details()
        return self.checkout_details


    def calculate_cart_base_total_amount(self):
        for cart_item in self.cart_items:
            self.cart_base_total_amount = cart_item.item.price * cart_item.quantity

    def get_campaign_discounts(self):
        campaign_helper = CampaignHelper(self.cart_items)
        self.discounts['campaigns'] = campaign_helper.get_campaign_discounts()


    def calculate_discount_amounts(self):
        try:
            for discount in self.discounts.get('campaigns', []):
                if discount.discount_type == 'Amount':
                    self.campaign_discount_amounts.append(discount.amount.get('amount'))
                if discount.discount_type == 'Rate':
                    self.campaign_discount_amounts.append((self.cart_base_total_amount *
                                                           discount.amount.get('rate')) / 100)

            for discount in self.discounts.get('coupons', []):
                self.coupon_discount_amount = (self.cart_base_total_amount * discount.amount.get('rate')) / 100
        except Exception as e:
            print('Error when trying to calculating discount amounts {0}'.format(str(e)))


    def creating_data_for_the_report(self, l, t):
        d = l
        m = [t]
        #print(l)
        for j in range(len(m)):
            for i in range(len(d)):

                p = d[i]['stock_name']
                c = list(m[j].keys())
                q = m[j]
                if p == c[0]:
                    q[p] = q[p] + 1
                    q[c[2]][0] = q[c[2]][0] + 1

                if d[i]['category_name'] == c[1] and d[i]['total_discount'] == 0:
                    q[c[1]] = q[c[1]] + 1

                    for i in range(len(q) - 2):
                        #print(c,d[i]['product_name'])
                        if d[i]['product_name'] == c[2+i]:
                            q[c[2 + i]][1] =q[c[2 + i]][1] + 1

        return m[0]

    def get_total_amount_after_discounts(self):
        if len(self.campaign_discount_amounts) > 0:
            self.campaign_discount_amount = max(self.campaign_discount_amounts)
        self.cart_final_total_amount = self.cart_base_total_amount - (
                    self.campaign_discount_amount + self.coupon_discount_amount)

        return self.cart_final_total_amount

    def prepare_checkout_details(self):
        for discount in self.discounts.get('campaigns'):
            self.delivery_cost = discount.name

        for cart_item in self.cart_items:
            self.checkout_details['products'].append({'stock_name': self.delivery_cost,
                                                      'user': self.user.name,
                                                      'category_name': cart_item.item.category.title,
                                                      'product_name': cart_item.item.title,
                                                      'created_at': cart_item.created_at,
                                                      'updated_at': cart_item.updated_at,
                                                      'quantity': cart_item.quantity,
                                                      'unit_price': cart_item.item.price,
                                                      'total_price': self.cart_base_total_amount,
                                                      'total_discount':
                                                            self.campaign_discount_amount
                                                        })

