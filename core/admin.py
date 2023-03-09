from django.contrib import admin

from core.models import Bid, Image, Item, OrderStatus, Order

admin.site.register(Bid)
admin.site.register(Image)
admin.site.register(Item)
admin.site.register(Order)
admin.site.register(OrderStatus)
