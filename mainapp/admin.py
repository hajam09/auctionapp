from django.contrib import admin
from .models import CustomerProfile, Item

# Register your models here.
admin.site.register(CustomerProfile)
admin.site.register(Item)