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


# Delete it
class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dateOfBirth = models.DateField()


class Bid(BaseModel):
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bidder')
    price = models.DecimalField(max_digits=9, decimal_places=2)


class Image(BaseModel):
    image = models.ImageField(blank=True, null=True, upload_to='uploads/%Y/%m/%d')


class Item(BaseModel):
    class Type(models.TextChoices):
        BUY_IT_NOW = 'BUY_IT_NOW', _('Buy It Now')
        AUCTION = 'AUCTION', _('Auction')

    seller = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='sellerItems')
    buyer = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='buyerItems')
    title = models.CharField(max_length=1024)
    description = models.TextField(blank=True, null=True)
    expireDate = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.BUY_IT_NOW)
    images = models.ManyToManyField(Image, blank=True, related_name='itemImages')
    bidders = models.ManyToManyField(Bid, blank=True, related_name='itemBids')
