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

from core.forms import LoginForm, RegistrationForm, ItemForm
from core.models import Item, Bid
from core.utils import emailOperations, generalOperations


# TODO: Item edit page.


def index(request):
    # expiredItems = Item.objects.filter(Q(expireDate__isnull=False), Q(expireDate__gte=timezone.now()))
    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query')).prefetch_related(
            'itemReview').select_related('seller')
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
        form = ItemForm(request, request.POST, request.FILES)
        if form.is_valid():
            form.save()

        messages.info(
            request, 'Item added successfully.'
        )
        return redirect('core:new-listing')
    else:
        form = ItemForm(request)

    context = {
        'form': form
    }
    return render(request, 'core/newListing.html', context)


@login_required
def editListing(request, pk):
    try:
        item = Item.objects.get(pk=pk)
    except Item.DoesNotExist:
        raise Http404

    if request.method == 'POST':
        form = ItemForm(request, item, request.POST, request.FILES)
        if form.is_valid():
            form.update()

        messages.info(
            request, 'Item updated successfully.'
        )

        return redirect('core:edit-listing', pk=pk)
    else:
        form = ItemForm(request, item)

    context = {
        'form': form
    }
    return render(request, 'core/editListing.html', context)


@login_required
def userListings(request):
    if request.GET.get('function') == 'delete' and request.GET.get('item'):
        Item.objects.filter(id=request.GET.get('item'), seller=request.user, deleteFl=False).update(deleteFl=True)
        return redirect('core:user-listings')

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
    # TODO: re-design the template from the image
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
    # TODO: Move components to template tag
    # TODO: Allow user to add price for auction
    # TODO: Show related products
    try:
        item = Item.objects.get(id=pk)
    except Item.DoesNotExist:
        raise Http404

    context = {
        'item': item
    }
    return render(request, 'core/itemView.html', context)


def itemsFromUser(request, pk):
    filterList = [
        reduce(
            operator.and_, [Q(**{'seller_id': pk})]
        )
    ]
    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query'), filterList).prefetch_related(
            'itemReview')

    }
    return render(request, 'core/itemsFromUser.html', context)


@login_required
def cartView(request):
    userCart = request.session.get('cart')
    itemId = int(request.GET.get('id')) if request.GET.get('id') is not None else None
    if userCart is None or userCart == [] and not request.GET.get('function'):
        request.session['cart'] = []
        return redirect('core:index-view')

    if request.method == 'POST':
        Item.objects.filter(id__in=userCart).update(buyer_id=request.user.id)
        request.session['cart'] = []
        messages.success(
            request, 'Order is complete!'
        )
        return redirect('core:index-view')

    if request.GET.get('function') == 'add' and itemId not in userCart:
        userCart.append(itemId)
    elif request.GET.get('function') == 'remove' and itemId in userCart:
        userCart.remove(itemId)

    request.session['cart'] = userCart

    previousUrl = request.META.get('HTTP_REFERER')
    if previousUrl and request.GET.get('function'):
        return redirect(previousUrl)

    items = Item.objects.filter(id__in=userCart)
    context = {
        'itemList': items
    }
    return render(request, 'core/cartView.html', context)
