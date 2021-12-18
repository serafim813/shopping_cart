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
        self.cart_items = Cart.objects.extra({'created_at':"date(created_at)"}).values('created_at').annotate(day_total=Count('id'))
        days = []
        checkout_details = []
        for cart_item in self.cart_items:
            days.append(cart_item['created_at'])
            len_days = len(days) - 1
            self.daily_orders = Cart.objects.filter(created_at=days[len_days])
            checkout_details.append([])
            for daily_order in self.daily_orders:
                cart_helper = CartHelper(daily_order)
                checkout_detail = cart_helper.prepare_cart_for_checkout()
                if type(checkout_details) != bool:
                    checkout_details[len(checkout_details)-1].append(checkout_detail['products'][0])

        with open("first_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            for checkout_detail_day in checkout_details:
                discount = 0
                number = checkout_details.index(checkout_detail_day)
                day = days[number]
                file_writer.writerow([day])
                for checkout_detail in checkout_detail_day:
                    if checkout_detail['total_discount'] != 0:
                        discount = checkout_detail['total_price'] / checkout_detail['total_discount']
                    file_writer.writerow(
                        [checkout_detail['updated_at'].strftime("%m.%d.%Y %H:%M"), checkout_detail['product_name'], checkout_detail['total_price'], checkout_detail['total_discount'], discount])

        with open("second_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            data_for_report = ReportHelper.get_data_report(self, checkout_details, days, 0)
            for data in data_for_report:
                file_writer.writerow(data)

        with open("third_report.csv", mode="w", encoding='utf-8') as w_file:
            file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
            data_for_report = ReportHelper.get_data_report(self, checkout_details, days, 1)
            for data in data_for_report:
                file_writer.writerow(data)

    def update_results(self):
        update_results = []
        for i in range(len(self.results)):
            update_results.append({})
            update_results[i] = copy.deepcopy(self.results[i])
        return(update_results)

    def get_data_stock(self):
        self.results = []
        self.campaigns = Campaign.objects.all()
        for campaign in self.campaigns:
            self.results.append({})
            result = self.results[len(self.results)-1]
            name = campaign.name
            title = campaign.target_category.title
            id = campaign.target_category_id
            result[name] = 0
            result[title] = 0
            self.products = Product.objects.filter(category_id=id)
            for product in self.products:
                title = product.title
                result[title] = [0, 0]
        return self.results

    def get_data_report(self, checkout_details, days, count):
        data_for_report = []
        results = ReportHelper.get_data_stock(self)
        results = ReportHelper.update_results(self)
        for checkout_detail in checkout_details:
            number = checkout_details.index(checkout_detail)
            day = days[number]
            data_for_report.append([day])
            for result in results:
                results = ReportHelper.update_results(self)
                data_for_the_report = ReportHelper.creating_data_for_the_report(self, checkout_detail, result)
                data_keys = list(data_for_the_report.keys())
                if count == 0:
                    data_for_report.append([data_keys[0], data_keys[1], data_for_the_report[data_keys[0]],
                                          data_for_the_report[data_keys[1]]])
                if count == 1:
                    for i in range(len(data_for_the_report) - 2):
                        data_for_report.append([data_keys[0], data_keys[2 + i], data_for_the_report[data_keys[2 + i]][0],
                                              data_for_the_report[data_keys[2 + i]][1]])
        return data_for_report

    def creating_data_for_the_report(self, daily_orders, results):
        for daily_order in daily_orders:
            result = results
            stock_name = daily_order['stock_name']
            result_keys = list(result.keys())
            if stock_name == result_keys[0]:
                result[stock_name] = result[stock_name] + 1
                result[result_keys[2]][0] = result[result_keys[2]][0] + 1
            if daily_order['category_name'] == result_keys[1] and daily_order['total_discount'] == 0:
                result[result_keys[1]] = result[result_keys[1]] + 1
                for i in range(len(result) - 2):
                    if daily_order['product_name'] == result_keys[2+i]:
                        result[result_keys[2 + i]][1] = result[result_keys[2 + i]][1] + 1

        return results