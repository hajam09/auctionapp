import random

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    createdDttm = models.DateTimeField(default=timezone.now)
    modifiedDttm = models.DateTimeField(auto_now=True)
    reference = models.CharField(max_length=2048, blank=True, null=True)
    deleteFl = models.BooleanField(default=False)
    orderNo = models.IntegerField(default=1, blank=True, null=True)
    versionNo = models.IntegerField(default=1, blank=True, null=True)

    class Meta:
        abstract = True


class Item(BaseModel):
    class Type(models.TextChoices):
        BUY_IT_NOW = 'BUY_IT_NOW', _('Buy It Now')
        AUCTION = 'AUCTION', _('Auction')

    class Condition(models.TextChoices):
        NEW = 'NEW', _('New')
        USED = 'USED', _('Used')
        OPENED_NEVER_USED = 'OPENED_NEVER_USED', _('Opened – never used')
        SELLER_REFURBISHED = 'SELLER_REFURBISHED', _('Seller refurbished')
        FOR_PARTS_OR_NOT_WORKING = 'FOR_PARTS_OR_NOT_WORKING', _('For parts or not working')

    seller = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='sellerItems')
    buyer = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='buyerItems')
    title = models.CharField(max_length=1024)
    description = models.TextField(blank=True, null=True)
    expireDate = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    deliveryCharge = models.DecimalField(blank=True, null=True, max_digits=9, decimal_places=2)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.BUY_IT_NOW)
    condition = models.CharField(max_length=32, choices=Condition.choices, default=Condition.NEW)

    def __str__(self):
        return self.title

    def isExpired(self):
        return self.expireDate > timezone.now()


class Image(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemImage')
    image = models.ImageField(blank=True, null=True, upload_to='uploads/%Y/%m/%d')


class Bid(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemBid')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bidder')
    price = models.DecimalField(max_digits=9, decimal_places=2)


def generateOrderNumber():
    return random.randint(1000000000, 9999999999)


class Order(BaseModel):
    total = models.DecimalField(max_digits=9, decimal_places=2)
    number = models.CharField(max_length=16, unique=True, default=generateOrderNumber)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemOrder')
    quantity = models.PositiveSmallIntegerField()
    tracking = models.CharField(blank=True, null=True, max_length=64)


class OrderStatus(BaseModel):
    class Status(models.TextChoices):
        ORDERED = 'ORDERED', _('Ordered')
        PROCESSING = 'PROCESSING', _('Processing')
        CANCELLED = 'CANCELLED', _('Cancelled')
        DISPATCHED = 'DISPATCHED', _('Dispatched')
        DELIVERED = 'DELIVERED', _('Delivered')
        DISPUTED = 'DISPUTED', _('Disputed')
        RETURN_STARTED = 'RETURN_STARTED', _('Return Started')
        RETURN_ACCEPTED = 'RETURN_ACCEPTED', _('Return Accepted')
        RETURN_REJECTED = 'RETURN_REJECTED', _('Return Rejected')
        RETURNED = 'RETURNED', _('Returned')
        REFUNDED = 'REFUNDED', _('Refunded')

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DISPATCHED)
    description = models.TextField(blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderStatus')


class Review(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemReview')
    summary = models.CharField(max_length=1024)
    description = models.TextField(blank=True, null=True)
    rating = models.PositiveSmallIntegerField()
