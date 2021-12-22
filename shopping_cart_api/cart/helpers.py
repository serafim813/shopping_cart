from .models import Cart
from shopping_cart_api.discounts.helpers import CampaignHelper
from django.db.models import Count
from shopping_cart_api.discounts.models import Campaign
from shopping_cart_api.products.models import Category, Product
import csv
import copy

class CartHelper:

    def __init__(self, id):
        self.discount_type = []
        self.user = id.user
        self.id = id.id
        self.cart_base_total_amount = 0
        self.cart_final_total_amount = 0
        self.campaign_discount_amounts = []
        self.campaign_discount_amount = 0
        self.coupon_discount_amount = 0
        self.discount_name = 'Undiscounted'
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

    def get_total_amount_after_discounts(self):
        if len(self.campaign_discount_amounts) > 0:
            self.campaign_discount_amount = max(self.campaign_discount_amounts)
        self.cart_final_total_amount = self.cart_base_total_amount - (
                    self.campaign_discount_amount + self.coupon_discount_amount)

        return self.cart_final_total_amount

    def prepare_checkout_details(self):
        for discount in self.discounts.get('campaigns'):
            self.discount_name = discount.name

        for cart_item in self.cart_items:
            self.checkout_details['products'].append({'stock_name': self.discount_name,
                                                      'user': self.user.name,
                                                      'category_name': cart_item.item.category.title,
                                                      'product_name': cart_item.item.title,
                                                      'created_at': cart_item.created_at,
                                                      'updated_at': cart_item.updated_at,
                                                      'quantity': cart_item.quantity,
                                                      'unit_price': cart_item.item.price,
                                                      'total_price': self.cart_base_total_amount,
                                                      'total_discount': self.campaign_discount_amount})


class ReportHelper:
    def get_daily_orders(self):
        cart_items = Cart.objects.extra({'created_at':"date(created_at)"}).values('created_at').annotate(day_total=Count('id'))
        self.days = []
        self.checkout_details = []
        for cart_item in cart_items:
            self.days.append(cart_item['created_at'])
            len_days = len(self.days) - 1
            daily_orders = Cart.objects.filter(created_at=self.days[len_days])
            self.checkout_details.append([])
            for daily_order in daily_orders:
                cart_helper = CartHelper(daily_order)
                checkout_detail = cart_helper.prepare_cart_for_checkout()
                len_checkout_details = len(self.checkout_details) - 1
                if type(self.checkout_details) != bool:
                    self.checkout_details[len_checkout_details].append(checkout_detail['products'][0])

        with open("first_report.csv", mode="w", encoding='utf-8') as w_file:
            fw = csv.writer(w_file, delimiter=",", lineterminator="\r")
            for checkout_detail_day in self.checkout_details:
                discount = 0
                number = self.checkout_details.index(checkout_detail_day)
                day = self.days[number]
                fw.writerow([day])
                for checkout_detail in checkout_detail_day:
                    if checkout_detail['total_discount'] != 0:
                        discount = checkout_detail['total_price'] / checkout_detail['total_discount']
                    fw.writerow(
                        [checkout_detail['updated_at'].strftime("%m.%d.%Y %H:%M"), checkout_detail['product_name'], checkout_detail['total_price'], checkout_detail['total_discount'], discount])

        with open("second_report.csv", mode="w", encoding='utf-8') as w_file:
            fw = csv.writer(w_file, delimiter=",", lineterminator="\r")
            ReportHelper.get_data_report(self)
            for day in self.day_dict:
                fw.writerow([day])
                for stock in self.day_dict[day]:
                    for category in self.day_dict[day][stock]:
                        for count in self.day_dict[day][stock][category]:
                            count_one = self.day_dict[day][stock][category][count]
                            count_two = count_one[0]
                            count_three = count_one[1]
                            fw.writerow([stock, count, count_two, count_three])

        with open("third_report.csv", mode="w", encoding='utf-8') as w_file:
            fw = csv.writer(w_file, delimiter=",", lineterminator="\r")
            ReportHelper.get_data_report(self)
            for day in self.day_dict:
                fw.writerow([day])
                for stock in self.day_dict[day]:
                    for category in self.day_dict[day][stock]:
                        count_two = 0
                        count_three = 0
                        for count in self.day_dict[day][stock][category]:
                            count_one = self.day_dict[day][stock][category][count]
                            count_two += count_one[0]
                            count_three += count_one[1]
                        fw.writerow([stock, category, count_two, count_three])

    def update_results(self):
        update_results = {}
        for day in self.day_dict:
            update_results[day] = copy.deepcopy(self.day_dict[day])
        return update_results

    def get_data_stock(self):
        stock = {}
        self.day_dict = {}
        for day in self.days:
            for campaign in Campaign.objects.all():
                products_dict = {}
                category = {}
                name = campaign.name
                category_title = campaign.target_category.title
                id = campaign.target_category_id
                category[category_title] = products_dict
                stock[name] = category
                self.day_dict[day] = stock
                for product in Product.objects.filter(category_id=id):
                    product_title = product.title
                    products_dict[product_title] = [0, 0]
        return self.day_dict

    def get_data_report(self):
        ReportHelper.get_data_stock(self)
        for checkout_detail_day in self.checkout_details:
            number = self.checkout_details.index(checkout_detail_day)
            day = self.days[number]
            data_for_the_report = ReportHelper.creating_data_for_the_report(self, checkout_detail_day, day)

        return data_for_the_report

    def creating_data_for_the_report(self, checkout_detail_day, day):
        for checkout_detail in checkout_detail_day:
            stock_name = checkout_detail['stock_name']
            category_name = checkout_detail['category_name']
            product_name = checkout_detail['product_name']
            quantity = checkout_detail['quantity']
            self.day_dict = ReportHelper.update_results(self)
            if stock_name != 'Undiscounted':
                self.day_dict[day][stock_name][category_name][product_name][0] += quantity
            else:
                for category in Category.objects.filter(title=category_name):
                    category_id = category.id
                for campaign in Campaign.objects.filter(target_category=category_id):
                    campaign_name = campaign.name
                self.day_dict[day][campaign_name][category_name][product_name][1] += quantity

        return self.day_dict
