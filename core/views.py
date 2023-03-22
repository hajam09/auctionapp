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
from core.models import Item, Bid, Image, OrderStatus, Order, Review, Note
from core.utils import emailOperations, generalOperations


def index(request):
    # expiredItems = Item.objects.filter(Q(expireDate__isnull=False), Q(expireDate__gte=timezone.now()))
    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query')).select_related('seller')
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
        form = ItemForm(request, None, request.POST, request.FILES)
        if form.is_valid():
            form.save()

        messages.info(
            request, 'Item added successfully.'
        )
        return redirect('core:new-listing')
    else:
        form = ItemForm(request, None)

    context = {
        'form': form
    }
    return render(request, 'core/newListing.html', context)


@login_required
def editListing(request, pk):
    if request.GET.get('function') == 'deleteImage' and request.GET.get('image'):
        Image.objects.filter(id=request.GET.get('image'), item_id=pk, item__seller=request.user).delete()
        return redirect('core:edit-listing', pk=pk)

    try:
        item = Item.objects.get(pk=pk, seller=request.user)
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
        'form': form,
        'item': item,
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

    context = {
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query'), filterList).prefetch_related(
            'itemOrders')
    }
    return render(request, 'core/userListings.html', context)


@login_required
def userPurchases(request):
    # TODO: View order details
    # TODO: More actions: CONTACT_SELLER | RETURN_THIS_ITEM | ADD_REVIEW_FOR_ORDER | DIDNT_RECEIVE_IT | ADD_NOTE

    if request.method == 'POST' and 'ADD_REVIEW_FOR_ORDER' in request.POST:
        Review.objects.create(
            order_id=request.POST.get('order-id'),
            summary=request.POST.get('summary'),
            description=request.POST.get('description'),
            rating=request.POST.get('rating'),
        )
        messages.success(
            request,
            f'Your review has been added for order #{request.POST.get("order-number")}'
        )
        return redirect('core:user-purchases')

    elif request.method == 'POST' and 'ADD_NOTE_FOR_ORDER' in request.POST:
        Note.objects.create(
            order_id=request.POST.get('order-id'),
            summary=request.POST.get('summary'),
            description=request.POST.get('description')
        )
        messages.success(
            request,
            f'Note added successfully for order #{request.POST.get("order-number")}'
        )
        return redirect('core:user-purchases')

    filterList = [
        reduce(
            operator.and_, [Q(**{'buyer_id': request.user.id})]
        )
    ]
    orderList = generalOperations.performComplexOrderSearch(request.GET.get('query'), filterList).select_related(
        'item__seller'
    )
    orderStatusList = OrderStatus.objects.filter(
        order_id__in=orderList.values_list('id', flat=True)
    ).select_related('order').order_by('order', '-createdDttm').distinct('order')

    context = {
        'orderList': orderList,
        'orderStatusList': orderStatusList
    }
    return render(request, 'core/userPurchases.html', context)


@login_required
def userBids(request):
    bids = Bid.objects.filter(bidder=request.user).values_list('item_id', 'item__price', 'item__type').annotate(
        Max('price')
    )
    latestPriceForEachBids = Bid.objects.filter(
        item_id__in=bids.values_list('item_id', flat=True)
    ).select_related('item').order_by('item', '-createdDttm').distinct('item')

    context = {
        'bids': bids,
        'latestPriceForEachBids': latestPriceForEachBids,
    }
    return render(request, 'core/userBids.html', context)


@login_required
def itemBids(request, pk):
    context = {
        'bids': Bid.objects.filter(item_id=pk).select_related('bidder')
    }
    return render(request, 'core/itemBids.html', context)


def itemView(request, pk):
    # TODO: Show related products
    try:
        item = Item.objects.get(id=pk)
    except Item.DoesNotExist:
        raise Http404

    if request.method == 'POST' and 'addToCart' in request.POST:
        userCart = request.session.get('cart', {})
        userCart[pk] = int(request.POST.get('quantity'))
        request.session['cart'] = userCart
        return redirect('core:item-view', pk=pk)

    elif request.method == 'POST' and 'submitBidForItem' in request.POST:
        bidAmount = float(request.POST.get('bidAmount'))
        latestBid = Bid.objects.filter(item_id=pk).last()
        currentPrice = latestBid.price if latestBid else item.price

        if bidAmount <= float(currentPrice):
            messages.error(
                request,
                'Bid amount must be higher than current bid value.'
            )
        else:
            Bid.objects.create(
                item_id=pk, bidder_id=request.user.id, price=bidAmount
            )
        return redirect('core:item-view', pk=pk)

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
        'itemList': generalOperations.performComplexItemSearch(request.GET.get('query'), filterList).select_related(
            'seller')
    }
    return render(request, 'core/itemsFromUser.html', context)


@login_required
def cartView(request):
    userCart = request.session.get('cart', {})

    if request.method == 'POST':
        items = Item.objects.filter(id__in=userCart.keys())
        orderList = []
        orderStatusList = []

        for item in items:
            # total = price * quantity + delivery
            total = item.price * userCart.get(str(item.id))
            total += item.deliveryCharge if item.deliveryCharge else 0
            order = Order(item=item, buyer=request.user, total=total, quantity=userCart.get(str(item.id)))
            orderStatus = OrderStatus(status=OrderStatus.Status.ORDERED, order=order)
            orderList.append(order)
            orderStatusList.append(orderStatus)

        Order.objects.bulk_create(orderList)
        OrderStatus.objects.bulk_create(orderStatusList)
        request.session['cart'] = {}
        messages.success(
            request, 'Order is complete!'
        )
        return redirect('core:index-view')

    if request.GET.get('function') == 'removeFromCart':
        userCart.pop(request.GET.get('id'), None)

    elif request.GET.get('function') == 'addToCart':
        quantity = request.GET.get('quantity', 1)
        userCart[request.GET.get('id')] = int(quantity)

    elif request.GET.get('function') == 'increaseQuantity':
        currentStock = Item.objects.get(id=request.GET.get('id')).stock
        currentQuantity = userCart.get(request.GET.get('id'))

        if currentQuantity + 1 > currentStock:
            messages.warning(
                request, 'Not enough stock!'
            )
        else:
            userCart[request.GET.get('id')] += 1

    elif request.GET.get('function') == 'decreaseQuantity':
        currentQuantity = userCart.get(request.GET.get('id'))

        if currentQuantity - 1 == 0:
            userCart.pop(request.GET.get('id'), None)
        else:
            userCart[request.GET.get('id')] -= 1

    request.session['cart'] = userCart

    previousUrl = request.META.get('HTTP_REFERER')
    if previousUrl and request.GET.get('function'):
        return redirect(previousUrl)

    items = Item.objects.filter(id__in=userCart.keys())
    context = {
        'itemList': items
    }
    return render(request, 'core/cartView.html', context)
