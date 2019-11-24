from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse, Http404, QueryDict, JsonResponse
#from django.template import RequestContext, loader
#from django.contrib.auth.hashers import make_password
#from django.db import IntegrityError
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login as auth_login
#from django.urls import reverse
import re, time
from .models import CustomerProfile, Item
from django.views.decorators.csrf import csrf_exempt
#from django.views.generic import TemplateView
from django.core.files.storage import FileSystemStorage
from datetime import datetime
#from django.core.mail import send_mail
#from djutils.decorators import async

# Create your views here.
def checkExpire():
	u = Item.objects.all()
	for i in u:
		if(timezone.now()>i.expiredate):
			Item.objects.filter(id=i.pk).update(status=True)

def index(request):
	checkExpire()
	if request.method=="GET":
		try:
			keyword2 = request.GET["searchvalue"]
			keyword = ''.join([i for i in keyword2 if i.isalpha()])
			search_results = []

			if keyword:

				search_results = Item.objects.filter(title__icontains=keyword, status=False) | \
                                Item.objects.filter(description__icontains=keyword, status=False)

			if len(search_results) == 0:
				return HttpResponse("No results found, search for something more specific.")
			return JsonResponse({"items": list(search_results.values())})
		except:
			pass
	return render(request,'mainapp/frontpage.html',{"items": Item.objects.filter(status=False)})

@csrf_exempt
def login(request):
	checkExpire()
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(username=username, password=password)
		if user:
			auth_login(request, user)
		else:
			return HttpResponse("Username and Password didn't match!")
	return render(request,'mainapp/login.html', {})

@csrf_exempt
def signup(request):
	checkExpire()
	if request.method == 'POST':
		fullname = request.POST['fullname'].split(" ")
		fname = " ".join(fullname[:len(fullname)-1])
		sname = "".join(fullname[len(fullname)-1])
		email = request.POST['email']
		password = request.POST['password']
		birthDate = request.POST['birthDate']

		checkAccountExist = CustomerProfile.objects.filter(email=email)
		if(len(checkAccountExist)==0):
			user = User.objects.create_user(username=email, password=password, first_name=fname, last_name=sname)
			user.customerprofile_set.create(birthDate=birthDate, email=email)
			return render(request,'mainapp/login.html', {})
		return HttpResponse("An account already exists for this email address, please try again!")
	return render(request,'mainapp/signup.html', {})

@csrf_exempt
def log_out(request):
	checkExpire()
	"""Log out - note that the session will be deleted"""
	request.session.flush()
	logout(request)
	return redirect('mainapp:index')

def new_item(request):
	checkExpire()
	user_pk = request.user.pk
	if(not user_pk):
		return redirect('mainapp:login')
	try:
		if("newitem" in request.POST):
			seller = User.objects.get(pk=user_pk)
			title = request.POST['title']
			description = request.POST['description']
			#description = re.match(r'[a-zA-Z0-9,. ]+$', description)
			description = description.replace("'", "").replace('"','')
			expiredate = request.POST['expiredate'].replace("T", " ")
			expiredate = expiredate.split(":")
			price = request.POST['price']
			expiredate = expiredate[0]+":"+expiredate[1]
			expiredate = datetime.strptime(expiredate, "%Y-%m-%d %H:%M")
			document = request.FILES["document"]
			fs = FileSystemStorage()
			imagename = fs.save(document.name, document)
			imageurl = fs.url(imagename)
			Item.objects.create(seller=seller, title=title, description=description, expiredate=expiredate, imagename=imagename, imageurl=imageurl, price=price, buyer=seller, status=False)
			print("New Item Created")
	except:
		pass
	return render(request,'mainapp/newitem.html')

@csrf_exempt
def closedauction(request):
	checkExpire()
	allitems = Item.objects.all()
	#Contains item objects which are expired and bought by someone else.
	closedItem = [item for item in allitems if timezone.now()>item.expiredate]
	try:
		return render(request,'mainapp/closedAuctions.html', {"items": closedItem})
	except:
		return render(request,'mainapp/closedAuctions.html')


@csrf_exempt
def update_profile(request):
	user_pk = request.user.pk
	if(not user_pk):
		return redirect('mainapp:login')
	customer_account = User.objects.get(pk=user_pk)
	customer_details = CustomerProfile.objects.get(userid=customer_account)
	fullname =  str(customer_account.first_name +" "+ customer_account.last_name)
	context = {"fullname": fullname, "email": customer_details.email}

	if request.method == "PUT":
		put = QueryDict(request.body)

		fullname = put.get('fullname').split(" ")
		fname = " ".join(fullname[:len(fullname)-1])
		sname = "".join(fullname[len(fullname)-1])
		email = put.get('email')

		User.objects.filter(pk=int(user_pk)).update(username=email, first_name=fname, last_name=sname)
		u = User.objects.get(pk=int(user_pk))

		if(put.get('password')):
			#User changed the password
			u.set_password(put.get('password'))
			u.save()
		#Updating the user profile
		CustomerProfile.objects.filter(pk=int(customer_details.pk)).update(email=email)
		return HttpResponse("Your details are updated!")
	return render(request,'mainapp/profilepage.html', context)

@csrf_exempt
def itempage(request):
	if request.method =="PUT":
		put = QueryDict(request.body)
		userbidvalue = round(float(put.get('userbidvalue')),2)
		itempkvalue = put.get('pkvalue')
		itemobject = Item.objects.get(pk=int(itempkvalue))

		if(userbidvalue>itemobject.price):
			user_pk = request.user
			#New bidder
			newbidlist = itemobject.bidders+user_pk.username+" "+str(userbidvalue)+","
			newbidlist = newbidlist.replace('"','').replace("'","")
			#Update buyer
			buyer = User.objects.get(pk=user_pk.pk)
			Item.objects.filter(pk=int(itempkvalue)).update(bidders=newbidlist,price=userbidvalue,buyer=buyer)
			return JsonResponse({"items": {"newprice": userbidvalue, "bidderid": user_pk.username}})
		else:
			return HttpResponse("Your bidding value is too small!")


	if request.method =="GET":
		try:
			itemid = request.GET["itemid"]
			outputData = Item.objects.filter(pk=int(itemid))
			return JsonResponse({"items": list(outputData.values())})
		except:
			pass
	return render(request,'mainapp/itempage.html', {})

def user_biddings(request):
	user_pk = request.user.username
	return render(request,'mainapp/userbiddings.html', {"items": Item.objects.filter(bidders__icontains=user_pk), "username": user_pk})