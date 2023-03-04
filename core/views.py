import operator
from functools import reduce
from http import HTTPStatus

from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.encoding import DjangoUnicodeDecodeError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from core.forms import LoginForm, RegistrationForm
from core.models import Item, Image
from core.utils import emailOperations, generalOperations


def index(request):
    # expiredItems = Item.objects.filter(Q(expireDate__isnull=False), Q(expireDate__gte=timezone.now()))
    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query'))
    }
    return render(request, 'core/index.html', context)


def login(request):
    if not request.session.session_key:
        request.session.save()

    if request.method == 'POST':
        uniqueVisitorId = request.session.session_key

        if cache.get(uniqueVisitorId) is not None and cache.get(uniqueVisitorId) > 3:
            cache.set(uniqueVisitorId, cache.get(uniqueVisitorId), 600)

            messages.error(
                request, 'Your account has been temporarily locked out because of too many failed login attempts.'
            )
            return redirect('core:login')

        form = LoginForm(request, request.POST)

        if form.is_valid():
            cache.delete(uniqueVisitorId)
            redirectUrl = request.GET.get('next')
            if redirectUrl:
                return redirect(redirectUrl)
            return redirect('core:index-view')

        if cache.get(uniqueVisitorId) is None:
            cache.set(uniqueVisitorId, 1)
        else:
            cache.incr(uniqueVisitorId, 1)

    else:
        form = LoginForm(request)

    context = {
        'form': form
    }
    return render(request, 'core/login.html', context)


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            newUser = form.save()
            emailOperations.sendEmailToActivateAccount(request, newUser)

            messages.info(
                request, 'We\'ve sent you an activation link. Please check your email.'
            )
            return redirect('core:login')
    else:
        form = RegistrationForm()

    context = {
        "form": form
    }
    return render(request, 'core/signup.html', context)


def activateAccount(request, encodedId, token):
    try:
        uid = force_str(urlsafe_base64_decode(encodedId))
        user = User.objects.get(pk=uid)
    except (DjangoUnicodeDecodeError, ValueError, User.DoesNotExist):
        user = None

    passwordResetTokenGenerator = PasswordResetTokenGenerator()

    if user is not None and passwordResetTokenGenerator.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(
            request,
            'Account activated successfully'
        )
        return redirect('accounts:login')

    return render(request, 'core/activateFailed.html', status=HTTPStatus.UNAUTHORIZED)


def logout(request):
    request.session.flush()
    auth.logout(request)

    previousUrl = request.META.get('HTTP_REFERER')
    if previousUrl:
        return redirect(previousUrl)

    return redirect('core:index-view')


@login_required
def newListing(request):
    if request.method == 'POST':
        itemName = request.POST.get('item-name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        expireDate = request.POST.get('expire-date') or None
        sellType = Item.Type.AUCTION if expireDate else Item.Type.BUY_IT_NOW

        item = Item(
            seller=request.user,
            title=itemName,
            description=description,
            expireDate=expireDate,
            price=price,
            type=sellType,
        )

        item.save()
        imageList = Image.objects.bulk_create([Image(image=i) for i in request.FILES.getlist('images')])
        item.images.add(*imageList)

        messages.info(
            request, 'Item added successfully.'
        )
        return redirect('core:new-listing')

    return render(request, 'core/newListing.html')


@login_required
def userListings(request):
    filterList = [
        reduce(
            operator.and_, [Q(**{'seller_id': request.user.id})]
        )
    ]

    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query'), filterList)
    }
    return render(request, 'core/userListings.html', context)


@login_required
def itemBids(request, pk):
    return render(request, 'core/itemBids.html')


def itemView(request, pk):
    try:
        item = Item.objects.get(id=pk)
    except Item.DoesNotExist:
        raise Http404

    context = {
        'item': item
    }
    return render(request, 'core/itemView.html', context)


def closedauction(request):
    # checkExpire()
    # allitems = Item.objects.all()
    # Contains item objects which are expired and bought by someone else.
    # # closedItem = [item for item in allitems if timezone.now() > item.expiredate]
    # try:
    #     return render(request, 'core/closedAuctions.html', {"items": closedItem})
    # except:
    #     return render(request, 'core/closedAuctions.html')
    return render(request, 'core/closedAuctions.html')


# @csrf_exempt
def itempage(request):
    #     if request.method == "PUT":
    #         put = QueryDict(request.body)
    #         userbidvalue = round(float(put.get('userbidvalue')), 2)
    #         itempkvalue = put.get('pkvalue')
    #         itemobject = Item.objects.get(pk=int(itempkvalue))
    #
    #         if (userbidvalue > itemobject.price):
    #             user_pk = request.user
    #             # New bidder
    #             newbidlist = itemobject.bidders + user_pk.username + " " + str(userbidvalue) + ","
    #             newbidlist = newbidlist.replace('"', '').replace("'", "")
    #             # Update buyer
    #             buyer = User.objects.get(pk=user_pk.pk)
    #             Item.objects.filter(pk=int(itempkvalue)).update(bidders=newbidlist, price=userbidvalue, buyer=buyer)
    #             return JsonResponse({"items": {"newprice": userbidvalue, "bidderid": user_pk.username}})
    #         else:
    #             return HttpResponse("Your bidding value is too small!")
    #
    #     if request.method == "GET":
    #         try:
    #             itemid = request.GET["itemid"]
    #             outputData = Item.objects.filter(pk=int(itemid))
    #             return JsonResponse({"items": list(outputData.values())})
    #         except:
    #             pass
    return render(request, 'core/itempage.html', {})


#
#
def user_biddings(request):
    #     user_pk = request.user.username
    #     return render(request, 'core/userbiddings.html',
    #                   {"items": Item.objects.filter(bidders__icontains=user_pk), "username": user_pk})
    return render(request, 'core/itempage.html', {})
