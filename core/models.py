import random

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generateOrderNumber():
    return random.randint(1000000000, 9999999999)


class BaseModel(models.Model):
    createdDttm = models.DateTimeField(default=timezone.now)
    modifiedDttm = models.DateTimeField(auto_now=True)
    reference = models.CharField(max_length=2048, blank=True, null=True)
    deleteFl = models.BooleanField(default=False)
    orderNo = models.IntegerField(default=1, blank=True, null=True)
    versionNo = models.IntegerField(default=1, blank=True, null=True)

    class Meta:
        abstract = True


class Address(BaseModel):
    class Country(models.TextChoices):
        GB = 'GB', _('United Kingdom')

    user = models.OneToOneField(User, on_delete=models.DO_NOTHING, related_name='address')
    addressLine1 = models.CharField(max_length=32)
    addressLine2 = models.CharField(max_length=32)
    town = models.CharField(max_length=32)
    county = models.CharField(max_length=32)
    postcode = models.CharField(max_length=32)
    country = models.CharField(max_length=32, choices=Country.choices, default=Country.GB)

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

    seller = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='sellerItems')
    title = models.CharField(max_length=1024)
    description = models.TextField(blank=True, null=True)
    expireDate = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    deliveryCharge = models.DecimalField(blank=True, null=True, max_digits=9, decimal_places=2)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.BUY_IT_NOW)
    condition = models.CharField(max_length=32, choices=Condition.choices, default=Condition.NEW)
    stock = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.title

    def isExpired(self):
        return self.expireDate > timezone.now()


class Image(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemImages')
    image = models.ImageField(upload_to='uploads/%Y/%m/%d')


class Bid(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemBids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bidderBids')
    price = models.DecimalField(max_digits=9, decimal_places=2)


class Order(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='itemOrders')
    buyer = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='buyerOrders')
    total = models.DecimalField(max_digits=9, decimal_places=2)
    number = models.CharField(max_length=16, unique=True, default=generateOrderNumber)
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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderReviews')
    summary = models.CharField(max_length=1024)
    description = models.TextField()
    rating = models.PositiveSmallIntegerField()


class Note(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderNotes')
    summary = models.CharField(max_length=1024)
    description = models.TextField()


class Communication(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderCommunications')
    message = models.TextField()
