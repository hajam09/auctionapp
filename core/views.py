import operator
from functools import reduce
from http import HTTPStatus

from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.db.models import Q, Max
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.encoding import DjangoUnicodeDecodeError, force_str
from django.utils.http import urlsafe_base64_decode

from core.forms import LoginForm, RegistrationForm
from core.models import Item, Image, Bid
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
    return render(request, 'core/register.html', context)


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
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        expireDate = request.POST.get('expire-date') or None
        sellType = Item.Type.AUCTION if expireDate else Item.Type.BUY_IT_NOW
        condition = Item.Condition[request.POST.get('condition')]

        item = Item(
            seller=request.user,
            title=name,
            description=description,
            expireDate=expireDate,
            price=price,
            type=sellType,
            condition=condition,
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

    itemList = generalOperations.performComplexItemSearch(request.GET.get('query'), filterList).select_related('buyer')
    context = {
        'itemList': itemList
    }
    return render(request, 'core/userListings.html', context)


@login_required
def userPurchases(request):
    filterList = [
        reduce(
            operator.and_, [Q(**{'buyer_id': request.user.id})]
        )
    ]

    itemList = generalOperations.performComplexItemSearch(request.GET.get('query'), filterList)
    context = {
        'itemList': itemList
    }
    return render(request, 'core/userPurchases.html', context)


@login_required
def userBids(request):
    bids = Bid.objects.filter(bidder=request.user).values_list('item_id', 'item__price', 'item__type').annotate(
        Max('price')
    )

    context = {
        'bids': bids
    }
    return render(request, 'core/userBids.html', context)


@login_required
def itemBids(request, pk):
    context = {
        'bids': Bid.objects.filter(item_id=pk).select_related('bidder')
    }
    return render(request, 'core/itemBids.html', context)


def itemView(request, pk):
    try:
        item = Item.objects.get(id=pk)
    except Item.DoesNotExist:
        raise Http404

    context = {
        'item': item
    }
    return render(request, 'core/itemView.html', context)
