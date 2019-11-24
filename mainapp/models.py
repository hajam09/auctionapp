from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class CustomerProfile(models.Model):
	userid = models.OneToOneField(User, on_delete=models.CASCADE)#Onetoone
	birthDate = models.DateField()
	email = models.CharField(max_length=1000, default="")

class Item(models.Model):
	seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller')
	title = models.CharField(max_length=1000)
	description = models.CharField(max_length=9999)
	expiredate =  models.DateTimeField()
	imagename = models.CharField(max_length=1000)
	imageurl = models.CharField(max_length=1000)
	bidders = models.CharField(max_length=9999, default="")
	price = models.DecimalField(max_digits=9, decimal_places=2, null=True)
	status = models.BooleanField(default=False)
	buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='buyer')

	def __str__ (self):
		return self.title
