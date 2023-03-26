import datetime
import decimal
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from faker import Faker

from core.models import Item, Bid, Order, OrderStatus
from core.utils import generalOperations


class Command(BaseCommand):
    PASSWORD = 'admin'
    USER_COUNT = 10
    ITEM_FOR_EACH_USER = 80
    BIDS_PER_ITEM = 30
    ORDERS_PER_ITEM = 50

    def __init__(self):
        super().__init__()
        self.faker = Faker('en_GB')
        self.itemConditionList = [i[0] for i in Item._meta.get_field('condition').choices]
        self.utcNow = datetime.datetime.utcnow()
        self.counter = 1
        self.allUsers = None

    def handle(self, *args, **options):
        try:
            adminUser = User(
                username='admin',
                email='django.admin@example.com',
                first_name='Django',
                last_name='Admin',
                is_staff=True,
                is_active=True,
                is_superuser=True,
            )
            adminUser.set_password(Command.PASSWORD)
            adminUser.save()
        except IntegrityError:
            pass

        OrderStatus.objects.all().delete()
        Order.objects.all().delete()
        Bid.objects.all().delete()
        Item.objects.all().delete()
        User.objects.filter(is_staff=False).delete()
        print('Attempting to seed data')

        try:
            with transaction.atomic():
                pass
                print(f'Attempting to create {Command.USER_COUNT} users.')
                self.bulkCreateUsers()
                self.allUsers = User.objects.all()

                print(f'Attempting to create {Command.ITEM_FOR_EACH_USER} item listings for each users')
                self.bulkCreateItems()

                print(f'Attempting to create bidding for Auction items')
                self.bulkCreateBidForAuctionItems()

                print(f'Attempting to create Order for BUY_IT_NOW items')
                self.bulkCreateOrderAndOrderStatusForBuyItNowItems()

                print('Item seeding complete.')
        except BaseException:
            print('Failed to seed data. Rolled back all the transactions')

    def bulkCreateUsers(self):
        User.objects.bulk_create(
            [
                self.createUser() for _ in range(Command.USER_COUNT)
            ]
        )

    def bulkCreateItems(self):
        itemList = []
        for user in self.allUsers:
            itemList.extend(self.createItem(user))
        Item.objects.bulk_create(itemList, Command.ITEM_FOR_EACH_USER)

    def bulkCreateBidForAuctionItems(self):
        bidList = []
        for item in Item.objects.filter(type=Item.Type.AUCTION):
            for i in range(Command.BIDS_PER_ITEM):
                randomUser = random.choice(self.allUsers)
                latestBidForThisItem = Bid.objects.filter(item=item).last()
                randomPrice = float(decimal.Decimal(random.randrange(0, 1000)) / 100)
                price = float((latestBidForThisItem.price if latestBidForThisItem else item.price))
                price += randomPrice
                bidList.append(Bid(item=item, bidder=randomUser, price=price))
        Bid.objects.bulk_create(bidList, Command.BIDS_PER_ITEM)

    def bulkCreateOrderAndOrderStatusForBuyItNowItems(self):
        orderList = []
        orderStatusList = []
        buyItNowItems = Item.objects.filter(type=Item.Type.BUY_IT_NOW)
        for item in buyItNowItems:
            for i in range(Command.ORDERS_PER_ITEM):
                randomUser = random.choice(self.allUsers)
                orderedQuantity = random.randint(1, 15)
                total = generalOperations.calculateTotalPriceForOrder(item, orderedQuantity, True)
                if total is None:
                    # Skip this order because not enough stock left for this item.
                    continue
                item.stock -= orderedQuantity
                order = Order(item=item, buyer=randomUser, total=total, quantity=orderedQuantity)
                orderStatus = OrderStatus(status=OrderStatus.Status.ORDERED, order=order)
                orderList.append(order)
                orderStatusList.append(orderStatus)

        Item.objects.bulk_update(buyItNowItems, ['stock'])
        Order.objects.bulk_create(orderList, Command.ORDERS_PER_ITEM)
        OrderStatus.objects.bulk_create(orderStatusList, Command.ORDERS_PER_ITEM)

    def createUser(self):
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        email = self._email(first_name.lower(), last_name.lower())

        user = User()
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = email
        user.set_password(Command.PASSWORD)
        return user

    def _email(self, first_name, last_name):
        return f'{first_name}.{last_name}@{self.faker.free_email_domain()}'

    def _username(self, first_name, last_name):
        username = f'@{first_name}{last_name}'
        return username

    def createItem(self, user):
        itemList = []
        for i in range(Command.ITEM_FOR_EACH_USER):
            isAuction = self.faker.pybool()
            item = Item()
            item.seller = user
            item.title = f"Item {self.counter}"  # self.faker.paragraph(nb_sentences=1)
            self.counter += 1
            item.description = self.faker.paragraph(nb_sentences=6)

            if isAuction:
                item.expireDate = self.utcNow + datetime.timedelta(
                    days=random.randint(0, 10),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                    hours=random.randint(0, 59)
                )
                item.type = Item.Type.AUCTION
            else:
                item.type = Item.Type.BUY_IT_NOW
                item.stock = self.faker.pyint()

            item.price = float(decimal.Decimal(random.randrange(0, 1000)) / 100)
            item.deliveryCharge = float(decimal.Decimal(random.randrange(0, 1000)) / 100)
            item.condition = random.choice(self.itemConditionList)
            itemList.append(item)

        return itemList
