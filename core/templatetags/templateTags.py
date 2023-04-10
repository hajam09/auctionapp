from django import template
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from core.models import Item, Bid, Image, Order, Review, OrderStatus, Note, Address, PaymentMethod
from core.utils import generalOperations
from core.utils.navigationBar import Icon, linkItem

register = template.Library()

FULL_STAR = '<i class="fas fa-star"></i>'
HALF_STAR = '<i class="	fas fa-star-half-alt"></i>'
EMPTY_STAR = '<i class="far fa-star"></i>'


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Home', reverse('core:index-view'), None),
        linkItem('New listing', reverse('core:new-listing'), None),
    ]

    if request.user.is_authenticated:
        cart = request.session.get('cart', {})
        if len(cart) > 0:
            links.append(
                linkItem(f'Cart ({len(cart)})', reverse('core:cart-view'), None)
            )

        links.extend(
            [
                linkItem('Account', '', None, [
                    linkItem('My profile', reverse('core:profile-view'), Icon('', 'fa fa-user', '15')),
                    linkItem('My listings', reverse('core:user-listings'), Icon('', 'fas fa-th-list', '15')),
                    linkItem('My purchases', reverse('core:user-purchases'), Icon('', 'fa fa-shopping-bag', '15')),
                    linkItem('My Bidding\'s', reverse('core:user-bids'), Icon('', 'fa fa-gavel', '15')),
                    None,
                    linkItem('Logout', reverse('core:logout'), Icon('', 'fas fa-sign-out-alt', '15')),
                ]),
            ]
        )
    else:
        links.append(
            linkItem('Login / Register', '', None, [
                linkItem('Register', reverse('core:register'), Icon('', 'fas fa-user-circle', '20')),
                None,
                linkItem('Login', reverse('core:login'), Icon('', 'fas fa-sign-in-alt', '20')),
            ]),
        )
    return links


@register.simple_tag
def renderNavigationPanelComponent(panel):
    panelIcon = panel.get('icon') if panel.get('icon') else '<span></span>'
    if panel.get('subLinks') is None:
        itemContent = f'''
        <li class="nav-item active">
            <a class="nav-link" href="{panel.get('url')}" data-toggle="tooltip" data-placement="right"
               title="{panel.get('name')}">
                {panelIcon} {panel.get('name')}
            </a>
        </li>
        '''
    else:
        content = ''
        for subLink in panel.get('subLinks'):
            if subLink:
                content += f'''
                    <a class="dropdown-item"href="{subLink.get('url')}"> {subLink.get('icon')} {subLink.get('name')}</a>
                '''
            else:
                content += f'''<div class="dropdown-divider"></div>'''

        itemContent = f'''
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button"
               data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                {panelIcon} {panel.get('name')}
            </a>
            <div class="dropdown-menu dropdown-menu-right" aria-labelledby="navbarDropdown">
                {content}
            </div>
        </li>
        '''

    return mark_safe(itemContent)


@register.simple_tag
def cookieBanner():
    itemContent = f'''
        <div class="alert text-center cookiealert p-3 mb-2 bg-dark text-white" role="alert">
            <b>Do you like cookies?</b>
            &#x1F36A; We use cookies to ensure you get the best experience on our website.
            <a href="https://cookiesandyou.com/" target="_blank">Learn more</a>
            <button type="button" class="btn btn-primary btn-sm acceptcookies">I agree</button>
        </div>
    '''
    return mark_safe(itemContent)


@register.filter
def userBidStatus(bid, currentBidPrice):
    if bid[2] < currentBidPrice.price:
        return "You've been outbid!"
    return "You are the highest bidder!"


@register.simple_tag
def querySearchComponent(request):
    value = f"value='{request.GET.get('query')}'" if request.GET.get('query') else ''
    itemContent = f'''
    <form method="GET" action="{request.path}">
            <div class="row">
                <div class="col">
                    <input type="text" id="query" name="query" class="form-control col" {value}
                           placeholder="Search for anything..." required/>
                </div>
                <div class="col-auto">
                    <input type="submit" class="btn btn-outline-primary" value="Search"/>
                </div>
            </div>
        </form>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def itemCartButton(request, item):
    if not request.user.is_authenticated:
        return mark_safe('<span></span>')

    userCart = request.session.get('cart', {})

    if request.user == item.seller:
        return mark_safe(
            f'''
            <a class="btn btn-outline-dark mt-3" href="{reverse('core:edit-listing', kwargs={'pk': item.pk})}"
                role="button" style="margin-bottom: -25px;">
                <i class="fas fa-edit"></i>
                Edit item
            </a>
            '''
        )
    elif item.type == Item.Type.BUY_IT_NOW and item.id in userCart:
        return mark_safe(
            f'''
            <a class="btn btn-outline-secondary mt-3"
                href="{reverse('core:cart-view')}?function=remove&id={item.id}"
                role="button">
                    <i class="fas fa-cart-arrow-down"></i> Remove from cart
            </a>
            '''
        )
    elif item.type == Item.Type.BUY_IT_NOW and str(item.id) in userCart:
        return mark_safe(
            f'''
            <a class="btn btn-outline-primary mt-3"
                href="{reverse('core:cart-view')}?function=removeFromCart&id={item.id}"
                role="button">
                    <i class="fas fa-cart-plus"></i> Remove from cart
            </a>
            '''
        )
    elif item.type == Item.Type.BUY_IT_NOW and str(item.id) not in userCart:
        return mark_safe(
            f'''
            <a class="btn btn-outline-primary mt-3"
                href="{reverse('core:cart-view')}?function=addToCart&id={item.id}"
                role="button">
                    <i class="fas fa-cart-plus"></i> Add to cart
            </a>
            '''
        )

    return mark_safe('<span></span>')


def generateStarRatingFromFloat(rating):
    rating = round(rating * 2) / 2
    stars = ''
    for i in range(int(rating)):
        stars += FULL_STAR

    if rating - int(rating) == 0.5:
        stars += HALF_STAR

    for i in range(int(5 - rating)):
        stars += EMPTY_STAR

    return stars


def getItemSellingDetails(item, showSeller):
    sellerLine = f'''
        <li class="list-inline-item">
            All items from
            <a href="{reverse('core:items-from-user-view', kwargs={'pk': item.seller.pk})}" data-abc="true">{item.seller.get_short_name()}</a>
        </li>
        ''' if showSeller else '<span></span>'

    itemExpireDttm = f'''
        <li class="list-inline-item">
            <span class="text-muted" data-abc="true">Expires at {item.expireDate.strftime('%B %d, %Y %H:%M:%S')}</span>
        </li>
        ''' if item.type == Item.Type.AUCTION else '<span></span>'

    itemContent = f'''
        <ul class="list-inline list-inline-dotted mb-3 mb-lg-2">
            <li class="list-inline-item">
                <span class="text-muted" data-abc="true">{item.get_condition_display()}</span>
            </li>
            <li class="list-inline-item">
                <span class="text-muted" data-abc="true">{item.get_type_display()}</span>
            </li>
            {itemExpireDttm}
        </ul>
        <p class="mb-3">{item.description} </p>
        <ul class="list-inline list-inline-dotted mb-0">
            {sellerLine}
        </ul>
    '''
    return mark_safe(itemContent)


def getPurchaseOrderDetails(order, orderStatusList):
    orderStatus = next((os for os in orderStatusList if os.order == order), None)
    itemContent = f'''
        <ul class="list-inline list-inline-dotted mb-0">
            <li class="list-inline-item">Order date: {order.createdDttm.strftime('%d %h, %Y')}</li>
            &nbsp;&nbsp;&nbsp;
            <li class="list-inline-item">Order total: £{order.total}</li>
            &nbsp;&nbsp;&nbsp;
            <li class="list-inline-item">Order number: {order.number}</li>
        </ul>
        <ul class="list-inline list-inline-dotted mb-3 mb-lg-2">
            <li>Order status: {orderStatus.get_status_display()}</li>
            <li>Tracking number: {order.tracking if order.tracking else 'Not provided yet'}</li>
        </ul>
        <ul class="list-inline list-inline-dotted mb-0">
            <li class="list-inline-item">
                Sold by:
                <a href="/user/1/items" data-abc="true">{order.item.seller.get_short_name()}</a>
            </li>
        </ul>
    '''
    return mark_safe(itemContent)


def getItemPricingAndReviewDetails(request, item: Item, reviewList):
    averageRating = None
    itemReviews = [i for i in reviewList if i.order.item == item]
    if len(itemReviews) > 0:
        averageRating = sum([i.rating for i in itemReviews]) / len(itemReviews)
    rating = generateStarRatingFromFloat(averageRating) if averageRating else '<div style="height: 20px;"></div>'

    itemDelivery = f'''
        <p class="text-secondary" style="margin-bottom: -5px;">£{item.deliveryCharge} postage</p>
    ''' if item.deliveryCharge else f'<p class="text-success" style="margin-bottom: -5px;">Free shipping</p>'

    itemContent = f'''
        <div class="mt-3 mt-lg-0 ml-lg-3 text-center">
            <h3 class="mb-0 font-weight-semibold">£{item.price}</h3>
            <div>
                {rating}
            </div>
            <div class="text-muted">{len(itemReviews)} reviews</div>
            <div class="text-muted">{itemDelivery}</div>
            {itemCartButton(request, item)}
        </div>
        '''
    return mark_safe(itemContent)


def itemNoteModal(request, order: Order):
    itemContent = f'''
        <div class="modal fade" id="order-note-modal-{order.id}" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <form class="modal-content" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                    <input type="hidden" name="ADD_NOTE_FOR_ORDER">
                    <input type="hidden" name="order-id" value="{order.id}">
                    <input type="hidden" name="order-number" value="{order.number}">
                    <div class="modal-header">
                        <h5 class="modal-title">Add note for order #{order.number}</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <input class="form-control" type="text" name="summary" placeholder="Summary" required>
                        <br>
                        <textarea class="form-control" name="description" rows="3" placeholder="Description" required></textarea>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="submit" class="btn btn-primary">Add Note</button>
                    </div>
                </form>
            </div>
        </div>
        '''
    return itemContent


def itemReviewModal(request, order: Order):
    itemContent = f'''
        <div class="modal fade" id="item-review-modal-{order.id}" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <form class="modal-content" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                    <input type="hidden" name="order-id" value="{order.id}">
                    <input type="hidden" name="ADD_REVIEW_FOR_ORDER">
                    <input type="hidden" name="order-number" value="{order.number}">
                    <div class="modal-header">
                        <h5 class="modal-title">Review for order #{order.number}</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <input class="form-control" type="text" name="summary" placeholder="Summary" required>
                        <br>
                        <textarea class="form-control" name="description" rows="3" placeholder="Description" required></textarea>
                        <br>
                        <select class="form-control" name="rating" required>
                              <option value="1">1</option>
                              <option value="2">2</option>
                              <option value="3">3</option>
                              <option value="4">4</option>
                              <option value="5">5</option>
                            </select>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="submit" class="btn btn-primary">Submit Review</button>
                    </div>
                </form>
            </div>
        </div>
    '''
    return itemContent


def getMoreActionsDropdownContent(order: Order):
    itemContent = f'''
    <a class="dropdown-item" href="#">Contact seller</a>
    <a class="dropdown-item" href="#">Return this item</a>
    <a class="dropdown-item" data-toggle="modal" data-target="#item-review-modal-{order.id}">leave feedback</a>
    <a class="dropdown-item" href="#">I didn't receive it</a>
    <a class="dropdown-item" data-toggle="modal" data-target="#order-note-modal-{order.id}">Add note</a>
    <a class="dropdown-item" href="#">Hide order</a>
    '''
    return mark_safe(itemContent)


def getOrderDetailsAndMoreAction(request, order: Order):
    itemContent = f'''
        {itemNoteModal(request, order)}
        {itemReviewModal(request, order)}
        <div class="text-center" style="margin-top: -15px;">
            <ul class="no-bullets" style="list-style-type: none; margin: 0; padding: 0;">
                <li>
                    <a class="btn btn-primary mt-3" style="width: 100%;" href="{reverse('core:order-detail-view', kwargs={'pk': order.pk})}"
                       role="button">View order details
                    </a>
                </li>
                <li>
                    <a class="btn btn-outline-primary mt-3" style="width: 100%;" href="{reverse('core:items-from-user-view', kwargs={'pk': order.item.seller.pk})}"
                       role="button">View seller's other items
                    </a>
                </li>
                <li>
                    <div style="height: 15px"></div>
                    <a class="btn btn-outline-primary dropdown-toggle" href="#" role="button" style="width: 100%;"
                       id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true"
                       aria-expanded="false">
                        More actions
                    </a>
                    <div class="dropdown-menu" aria-labelledby="dropdownMenuLink"
                         style="width: 196px;">
                        {getMoreActionsDropdownContent(order)}
                    </div>
                </li>
            </ul>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemCatalogue(request, item, showItemImage, showSeller, showItemSellingDetails, showPurchaseOrderDetails,
                        showItemPricingAndReviewDetails, showOrderDetailsAndMoreAction, order=None,
                        orderStatusList=None, reviewList=None):
    showItemImage = eval(showItemImage)
    showSeller = eval(showSeller)
    showItemSellingDetails = eval(showItemSellingDetails)
    showPurchaseOrderDetails = eval(showPurchaseOrderDetails)
    showItemPricingAndReviewDetails = eval(showItemPricingAndReviewDetails)
    showOrderDetailsAndMoreAction = eval(showOrderDetailsAndMoreAction)

    # if showItemSellingDetails and showPurchaseOrderDetails:
    #     raise Exception('Cannot display both ItemSellingDetails and PurchaseOrderDetails.')
    #
    # if showItemPricingAndReviewDetails and showOrderDetailsAndMoreAction:
    #     raise Exception('Cannot display both ItemPricingAndReviewDetails and OrderDetailsAndMoreAction.')

    if showItemSellingDetails:
        secondComponent = getItemSellingDetails(item, showSeller)
    elif showPurchaseOrderDetails:
        secondComponent = getPurchaseOrderDetails(order, orderStatusList)
    else:
        raise Exception('Both showItemSellingDetails and showItemSellingDetails cannot be False.')

    if showItemPricingAndReviewDetails:
        thirdComponent = getItemPricingAndReviewDetails(request, item, reviewList=reviewList)
    elif showOrderDetailsAndMoreAction:
        thirdComponent = getOrderDetailsAndMoreAction(request, order)
    else:
        raise Exception('Both ItemPricingAndReviewDetails and OrderDetailsAndMoreAction cannot be False.')

    itemImage = f'''
        <div class="mr-2 mb-3 mb-lg-0">
            <img class="d-block w-100" src="https://dummyimage.com/150x150" width="150" height="150" alt="img">
        </div>
    ''' if showItemImage else '<span></span>'

    itemContent = f'''
        <div class="card card-body mt-3">
            <div class="media align-items-center align-items-lg-start text-center text-lg-left flex-column flex-lg-row">
                {itemImage}
                <div class="media-body">
                    <h6 class="media-title font-weight-semibold">
                        <a href="{reverse('core:item-view', kwargs={'pk': item.pk})}" data-abc="true">{item.title}</a>
                    </h6>
                    {secondComponent}
                </div>
                {thirdComponent}
            </div>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemCartProductCatalogue(request, item):
    cart = request.session.get('cart', {})
    itemContent = f'''
    <div class="card mb-3">
        <div class="card-body">
            <div class="d-flex justify-content-between">
                <div class="d-flex flex-row align-items-center">
                    <div>
                        <img class="img-fluid rounded-3" alt="Shopping item" style="width: 65px;"
                            src="https://mdbcdn.b-cdn.net/img/Photos/new-templates/bootstrap-shopping-carts/img1.webp"/>
                    </div>
                    &nbsp;&nbsp;&nbsp;&nbsp;
                    <div class="ms-3">
                        <h5>{item.title}</h5>
                        <p class="small mb-0">{f'{item.description[:70]}...' if len(item.description) > 70 else item.description}</p>
                    </div>
                </div>
                <div class="d-flex flex-row align-items-center">
                    <div style="width: 20%;">
                        <a class="btn btn-primary btn-sm" href="{reverse('core:cart-view')}?function=decreaseQuantity&id={item.id}" role="button">
                            <i class="fa fa-minus"></i>
                        </a>
                    </a>
                    </div>
                    <div style="width: 20%;">
                        <h5 class="fw-normal mb-0">{cart.get(str(item.id))}</h5>
                    </div>
                    <div style="width: 80px;">
                        <a class="btn btn-primary btn-sm" href="{reverse('core:cart-view')}?function=increaseQuantity&id={item.id}" role="button">
                            <i class="fa fa-plus"></i>
                        </a>
                    </div>
                    <div style="width: 80px;">
                        <h5 class="mb-0">£{item.price}</h5>
                    </div>
                    <a href="{reverse('core:cart-view')}?function=removeFromCart&id={item.id}" style="color: #cecece;">
                        <i class="fas fa-trash-alt"></i>
                    </a>
                </div>
            </div>
        </div>
    </div>    
    '''
    return mark_safe(itemContent)


def renderItemCartProductCatalogueList(request, itemList):
    itemContent = f'''
        <div class="col-lg-7">
            <h5 class="mb-3">
                <a href="#" class="text-body">
                <i class="fas fa-long-arrow-alt-left me-2">&nbsp;</i>Continue shopping</a>
            </h5>
            <hr>
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <p class="mb-0">You have {itemList.count()} item(s) in your cart</p>
                </div>
            </div>
            {"".join([renderItemCartProductCatalogue(request, item) for item in itemList])}
        </div>
    '''
    return mark_safe(itemContent)


def renderCardDetailsInputComponent(request, itemList):
    cart = request.session.get('cart', {})
    subtotal = 0
    delivery = 0
    for item in itemList:
        subtotal += item.price * cart.get(str(item.id))
        delivery += item.deliveryCharge if item.deliveryCharge else 0

    cards = ['amex', 'mastercard', 'paypal', 'stripe', 'visa']

    def getCardComponent(card):
        return f'''<a href="#" type="submit"><i class="fab fa-cc-{card} fa-2x me-2"></i></a>'''

    itemContent = f'''
    <div class="col-lg-5">
        <div class="card bg-light rounded-3">
            <form class="card-body" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5 class="mb-0">Card details</h5>
                </div>

                <p class="small mb-2">Card type</p>
                {'&nbsp;'.join([getCardComponent(card) for card in cards])}
                <div class="mt-4">
                    <div class="form-outline form-white mb-4">
                        <input type="text" id="cardHolderName" class="form-control form-control-lg" size="17"
                               placeholder="Cardholder's Name"/>
                        <label class="form-label" for="cardHolderName">Cardholder's Name</label>
                    </div>
                    <div class="form-outline form-white mb-4">
                        <input type="text" id="cardNumber" class="form-control form-control-lg" size="17"
                               placeholder="1234 5678 9012 3457" minlength="16" maxlength="16"/>
                        <label class="form-label" for="cardNumber">Card Number</label>
                    </div>
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="form-outline form-white">
                                <input type="text" id="expireDate" class="form-control form-control-lg" size="7"
                                       placeholder="MM/YYYY" id="exp" minlength="7" maxlength="7"/>
                                <label class="form-label" for="expireDate">Expiration</label>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-outline form-white">
                                <input type="password" id="cvv" class="form-control form-control-lg" size="1"
                                       placeholder="{3 * '&#9679;'}" minlength="3" maxlength="3"/>
                                <label class="form-label" for="cvv">CVV</label>
                            </div>
                        </div>
                    </div>
                </div>

                <hr class="my-4">

                <div class="d-flex justify-content-between">
                    <p class="mb-2">Subtotal</p>
                    <p class="mb-2">£{subtotal}</p>
                </div>

                <div class="d-flex justify-content-between">
                    <p class="mb-2">Shipping</p>
                    <p class="mb-2">£{delivery}</p>
                </div>

                <div class="d-flex justify-content-between mb-4">
                    <p class="mb-2">Total(Incl. taxes)</p>
                    <p class="mb-2">£{subtotal + delivery}</p>
                </div>

                <button type="submit" class="btn btn-dark btn-block btn-lg">
                    <div class="d-flex justify-content-between">
                        <span>£{subtotal + delivery}</span>
                        <span>Checkout&nbsp;&nbsp;<i class="fas fa-long-arrow-alt-right ms-2"></i></span>
                    </div>
                </button>
            </div>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderIndexViewTemplate(request, itemList):
    reviewList = Review.objects.filter(order__item_id__in=itemList).select_related('order__item__seller')
    itemContent = f'''
    {''.join([renderItemCatalogue(request, item, 'True', 'True', 'True', 'False', 'True', 'False', reviewList=reviewList) for item in itemList])}
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemsFromUserViewTemplate(request, itemList):
    reviewList = Review.objects.filter(order__item_id__in=itemList).select_related('order__item__seller')
    itemContent = f'''
    {''.join([renderItemCatalogue(request, item, 'True', 'False', 'True', 'False', 'True', 'False', reviewList=reviewList) for item in itemList])}
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderCartViewTemplate(request, itemList):
    itemContent = f'''
    <section class="h-100 h-custom">
        <div class="container py-5 h-100">
            <div class="row d-flex justify-content-center align-items-center h-100">
                <div class="col">
                    <div class="card">
                        <div class="card-body p-4">
                            <div class="row">
                                {renderItemCartProductCatalogueList(request, itemList)}
                                {renderCardDetailsInputComponent(request, itemList)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
    '''
    return mark_safe(itemContent)


@register.filter
def itemStatus(item):
    if item.type == Item.Type.AUCTION and item.isExpired() and item.itemOrders.count() == 0:
        return 'NOT SOLD'
    elif item.type == Item.Type.AUCTION and item.isExpired() and item.itemOrders.count() != 0:
        return 'SOLD'
    elif item.type == Item.Type.BUY_IT_NOW and item.stock == 0:
        return 'OUT OF STOCK'
    elif item.type == Item.Type.BUY_IT_NOW and item.stock > 0:
        return 'LISTED'
    raise Exception(f'Unknown status type found for item with id: {item.id}')


@register.simple_tag
def renderUserListingTable(item):
    viewBiddingButton = '<span></span>'
    if item.type == Item.Type.AUCTION:
        viewBiddingButton = f'''
            <a class="btn btn-outline-info btn-sm" href="{reverse('core:item-bids', kwargs={'pk': item.pk})}"
               data-toggle="tooltip" data-placement="top" title="View listing bids"
               role="button"><i class="fa fa-gavel" aria-hidden="true"></i></a>
        '''

    itemContent = f'''
        <tr>
            <th scope="row">{item.id}</th>
            <td><a href="{reverse('core:item-view', kwargs={'pk': item.pk})}">{item.title}</a></td>
            <td>
                <span class="badge badge-{'primary' if item.type == Item.Type.BUY_IT_NOW else 'secondary'}">
                    {item.get_type_display()}
                </span>
            </td>
            <td>£{item.price}</td>
            <td>{itemStatus(item)}</td>
            <td>
                <a class="btn btn-outline-dark btn-sm" href="{reverse('core:edit-listing', kwargs={'pk': item.pk})}"
                   data-toggle="tooltip" data-placement="top" title="Edit listing"
                   role="button"><i class="fa fa-edit"></i></a>
                <a class="btn btn-outline-danger btn-sm" href="{reverse('core:user-listings')}?function=delete&item={item.pk}"
                   data-toggle="tooltip" data-placement="top" title="Delete listing"
                   role="button"><i class='far fa-trash-alt'></i></a>
                   {viewBiddingButton}
            </td>
        </tr>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemImage(item, image):
    itemContent = f'''
        <div class="img-wraps">
            <a class="closes" title="Delete" style="padding-top: 0;"
                href="{reverse('core:edit-listing', kwargs={'pk': item.pk})}?function=deleteImage&image={image.pk}">×</a>
            <img class="img-responsive" src="{image.image.url}" alt="#" height="100" width="100">
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderUserBidsTable(bid, latestPriceForEachBids):
    currentBidPrice = next((lpb for lpb in latestPriceForEachBids if lpb.item.id == bid[0]), None)
    viewBiddingButton = '<span></span>'
    if bid[1] == Item.Type.AUCTION:
        viewBiddingButton = f'''
        <a class="btn btn-outline-secondary btn-sm" href="{reverse('core:item-bids', kwargs={'pk': bid[0]})}" role="button">View Bidding's</a>
        '''

    itemContent = f'''
        <tr>
            <th scope="row">{bid[0]}</th>
            <td>£{bid[2]}</td>
            <td>£{currentBidPrice.price}</td>
            <td>{userBidStatus(bid, currentBidPrice)}</td>
            <td>
                <a class="btn btn-outline-primary btn-sm" href="{reverse('core:item-view', kwargs={'pk': bid[0]})}"
                   role="button">View</a>
                   {viewBiddingButton}
            </td>
        </tr>
    '''
    return mark_safe(itemContent)


def getItemQuantityComponent(stock):
    itemContent = f'''
        <input type="hidden" name="addToCart">
        <div class="row" style="margin-left: -30px;">
            <div class="col-md-auto" style="padding-top: 8px;margin-left: 19px;">
                Quantity:
            </div>
            <div class="col" style="padding-left: 0;">
                <input class="form-control" type="number" name="quantity" value="1" max="{stock}" style="max-width: 10%;">
            </div>
            <div class="col" style="margin-left: -435px;padding-top: 4px;">
                <button type="submit" class="btn btn-outline-primary btn-sm">
                    <i class="fas fa-cart-plus"></i> Add to cart
                </button>
            </div>
        </div>
    '''
    return mark_safe(itemContent)


def getItemAuctionComponent(currentPrice):
    itemContent = f'''
        <input type="hidden" name="submitBidForItem">
        <div class="row" style="margin-left: -30px;">
            <div class="col-md-auto" style="padding-top: 8px;margin-left: 19px;">
                Bid amount:
            </div>
            <div class="col" style="padding-left: 0;">
                <input class="form-control" type="number" name="bidAmount" min={currentPrice} step=".1" style="max-width: 18%;" required>
            </div>
            <div class="col" style="margin-left: -360px;padding-top: 4px;">
                <button type="submit" class="btn btn-outline-primary btn-sm">
                    <i class="fa fa-arrow-up"></i> Submit bid
                </button>
            </div>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderOrderDetailViewComponent(request, order):
    # TODO: Create Note object from this component
    # TODO: Display delivery status
    # TODO: Display returns
    # TODO: Display delivery address
    if order.item.type == Item.Type.BUY_IT_NOW:
        itemPrice = order.item.price
    else:
        latestBid = Bid.objects.filter(item=order.item).last()
        itemPrice = latestBid.price if latestBid else order.item.price

    deliveryInfoStatus = OrderStatus.objects.filter(
        order=order, status__in=[
            OrderStatus.Status.ORDERED,
            OrderStatus.Status.PROCESSING,
            OrderStatus.Status.DISPATCHED,
            OrderStatus.Status.DELIVERED
        ]
    ).order_by('createdDttm')

    itemContent = f'''
        {itemNoteModal(request, order)}
        {itemReviewModal(request, order)}
        <h2>Order detail</h2>
        <div class="row" style="width: 1100px;">
            <div class="col-9">
                <div class="card">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-3">
                                <h5>Order info</h5>
                            </div>
                            <div class="col-9">
                                <dl class="row">
                                    <dd class="col-sm-3">Time Placed</dd>
                                    <dd class="col-sm-9">{order.createdDttm.strftime('%B %d, %Y %H:%M:%S')}</dd>

                                    <dd class="col-sm-3">Order number</dd>
                                    <dd class="col-sm-9">{order.number}</dd>

                                    <dd class="col-sm-3">Total</dd>
                                    <dd class="col-sm-9">£{order.total}</dd>

                                    <dd class="col-sm-3">Sold by</dd>
                                    <dd class="col-sm-9">{order.item.seller.get_full_name()}</dd>
                                </dl>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-3">
                                <h6>Delivery info</h6>
                            </div>
                            <div class="col-9">
                                <div class="progress-track">
                                    <ul id="deliverInfoProgressBar">
                                        <li class="step0 active" id="step1">Ordered - 22 Mar</li>
                                        <li class="step0 active text-center" id="step2">Processing</li>
                                        <li class="step0 active text-right" id="step3"><span
                                                id="three">Dispatched</span></li>
                                        <li class="step0 text-right" id="step4">Delivered</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-3">
                                <h6>Item details</h6>
                                <img class="d-block w-100" src="https://dummyimage.com/500x500" alt="img">
                            </div>
                            <div class="col-9" style="padding-top: 20px;">
                                <dl class="row">
                                    <dd class="col-sm-12">{order.item.title}</dd>

                                    <dd class="col-sm-4">Price</dd>
                                    <dd class="col-sm-8">£{itemPrice}</dd>

                                    <dd class="col-sm-4">Item number</dd>
                                    <dd class="col-sm-8">{order.item.id}</dd>

                                    <dd class="col-sm-4">Returns accepted</dd>
                                    <dd class="col-sm-8">through 24 Apr 2023.</dd>

                                    <br><br>
                                    <dd class="col-sm-4">
                                        <a href="#" class="btn btn-primary btn-sm active dropdown-toggle" role="button"
                                            id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true"
                                            aria-expanded="false">More actions</a>
                                        <div class="dropdown-menu" aria-labelledby="dropdownMenuLink"
                                             style="width: 196px;">
                                            {getMoreActionsDropdownContent(order)}
                                        </div>
                                    </dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-3 w-100">
                <h4>Delivery address</h4>
                <p style="margin-bottom:0;">Full name</p>
                <p style="margin-bottom:0;">Address line 1</p>
                <p style="margin-bottom:0;">Address line 2</p>
                <p style="margin-bottom:0;">Town</p>
                <p style="margin-bottom:0;">County</p>
                <p style="margin-bottom:0;">Postcode</p>
                <p style="margin-bottom:0;">Country</p>
            </div>
        </div>
        <br>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderOrderNotes(request, order):
    notes = ''
    for note in Note.objects.filter(order=order):
        description = note.description.replace("\n", "<br>")
        notes += f'''
        <div class="card">
            <div class="card-header">
                {note.summary}
                <button type="button" class="btn btn-secondary btn-sm float-right" style="margin-left: 10px;">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" class="btn btn-danger btn-sm float-right">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
            <div class="card-body">
                <blockquote class="blockquote mb-0">
                    <small>{description}</small>
                </blockquote>
            </div>
        </div>
        <br>
        '''

    itemContent = f'''
    <h4>Order notes</h2>
    {notes}
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemViewComponent(request, item):
    if item.type == Item.Type.BUY_IT_NOW:
        itemPrice = f'''
            <dd class="col-sm-2">Price:</dd>
            <dd class="col-sm-10">£{item.price}</dd>
        '''
        currentPrice = item.price
    else:
        latestBid = Bid.objects.filter(item=item).last()
        currentPrice = latestBid.price if latestBid else item.price
        itemPrice = f'''
            <dd class="col-sm-2">Current bid:</dd>
            <dd class="col-sm-10">£{currentPrice}</dd>
        '''

    imageList = Image.objects.filter(item=item)
    indicators = ''
    images = ''
    counter = 0

    for image in imageList:
        active = 'active' if image == imageList[0] else ''
        indicators += f'''<li data-target="#carousel" data-slide-to="{counter}" class="{active}"></li>'''
        images += f'''
        <div class="carousel-item {active}">
            <img class="d-block w-100" src="{image.image.url}" alt="First slide" height="450px;">
        </div>
        '''
        counter += 1
    else:
        images = f'''
        <div class="carousel-item active">
            <img class="d-block w-100" src="https://dummyimage.com/500x500" alt="img">
        </div>
        '''

    averageRating = Review.objects.filter(order__item=item).aggregate(avg=Avg('rating')).get('avg')
    rating = generateStarRatingFromFloat(averageRating) if averageRating else 'No ratings yet.'

    quantityOrBidComponent = f'''
        <div class="card bg-light">
            <div class="card-body">
                <form method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                    {getItemQuantityComponent(item.stock) if item.type == Item.Type.BUY_IT_NOW else getItemAuctionComponent(currentPrice)}
                </form>
            </div>
        </div>
    ''' if item.stock > 0 else '<span></span>'

    itemContent = f'''
    <div class="container-fluid p-3" style="max-width: 1500px;">
        <div class="row">
            <div class="col-6">
            <div id="carousel" class="carousel slide" data-ride="carousel">
                <ol class="carousel-indicators">
                    {indicators}
                </ol>
                <div class="carousel-inner">
                    {images}
                </div>
                <a class="carousel-control-prev" href="#carousel" role="button" data-slide="prev">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                    <span class="sr-only">Previous</span>
                </a>
                <a class="carousel-control-next" href="#carousel" role="button" data-slide="next">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                    <span class="sr-only">Next</span>
                </a>
            </div>
            </div>
            <div class="col-6 align-self-center">
                <h4>{item.title}</h4>
                <dl class="row">
                    <dd class="col-sm-2">Condition:</dd>
                    <dd class="col-sm-10">{item.get_condition_display()}</dd>

                    <dd class="col-sm-2">Ratings:</dd>
                    <dd class="col-sm-10">{rating}</dd>
                    
                    {itemPrice}

                    <dd class="col-sm-2">Stock:</dd>
                    <dd class="col-sm-10">{f'{item.stock} available' if item.stock > 0 else 'Out of stock.'}</dd>

                    <dd class="col-sm-2">Postage:</dd>
                    <dd class="col-sm-10">{'£' + str(item.deliveryCharge) if item.deliveryCharge else 'Free postage'}</dd>

                    <dd class="col-sm-2">Returns:</dd>
                    <dd class="col-sm-10">TODO</dd>
                </dl>
                {quantityOrBidComponent}
            </div>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


def getSimilarProductInstanceComponent(item: Item, columnSize: int):
    itemContent = f'''
    <div class="col-sm-{columnSize}">
        <div class="thumb-wrapper">
            <div class="img-box">
                <img src="https://dummyimage.com/500x500" class="img-fluid" alt="">
            </div>
            <div class="thumb-content">
                <h4>{item.title}</h4>
                <p class="item-price"><strike>$400.00</strike> <span>$369.00</span></p>
                <div class="star-rating">
                    <ul class="list-inline">
                        <li class="list-inline-item"><i class="fa fa-star"></i></li>
                        <li class="list-inline-item"><i class="fa fa-star"></i></li>
                        <li class="list-inline-item"><i class="fa fa-star"></i></li>
                        <li class="list-inline-item"><i class="fa fa-star"></i></li>
                        <li class="list-inline-item"><i class="fa fa-star-o"></i></li>
                    </ul>
                </div>
                <a href="#" class="btn btn-primary btn-sm">Add to Cart</a>
            </div>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def similarProductCarousel(item):
    ITEMS_PER_CAROUSEL = 4
    NUMBER_OF_CAROUSEL = 4

    items = generalOperations.performComplexItemSearch(
        f'{item.title}'
    ).filter(~Q(id=item.id))[:ITEMS_PER_CAROUSEL * NUMBER_OF_CAROUSEL]
    paginator = Paginator(items, ITEMS_PER_CAROUSEL)
    carouselItems = ''
    carouselIndicators = ''
    # TODO: Optimise query here. More NUMBER_OF_CAROUSEL means higher query search.

    for pageNumber in paginator.page_range:
        currentPage = paginator.page(pageNumber)
        containerSize = 12 // ITEMS_PER_CAROUSEL
        isActive = 'active' if pageNumber == 1 else ''
        classActive = 'class="active"' if isActive else ''

        carouselItems += f'''
        <div class="carousel-item {isActive}">
            <div class="row">
                {''.join([getSimilarProductInstanceComponent(item, containerSize) for item in currentPage.object_list])}
            </div>
        </div>
        '''

        carouselIndicators += f'''
            <li data-target="#myCarousel" data-slide-to="{pageNumber}" {classActive}></li>
        '''

    itemContent = f'''
    <div class="container-fluid p-3" style="max-width: 1500px;">
        <div class="row">
            <div class="col-md-12">
                <h2>Similar Products</h2>
                <div id="myCarousel" class="carousel slide" data-ride="carousel" data-interval="0">
                    <!-- Carousel indicators -->
                    <ol class="carousel-indicators">
                        {carouselIndicators}
                    </ol>
                    <!-- Wrapper for carousel items -->
                    <div class="carousel-inner">
                        {carouselItems}
                    </div>
                    <!-- Carousel controls -->
                    <a class="carousel-control-prev" href="#myCarousel" data-slide="prev">
                        <i class="fa fa-angle-left"></i>
                    </a>
                    <a class="carousel-control-next" href="#myCarousel" data-slide="next">
                        <i class="fa fa-angle-right"></i>
                    </a>
                </div>
            </div>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def paginationComponent(request, objects):
    if not objects.has_other_pages():
        return mark_safe('<span></span>')

    query = f"&query={request.GET.get('query')}" if request.GET.get('query') else ''

    if objects.has_previous():
        href = f'?page={objects.previous_page_number()}{query}'
        previousPageLink = f'''
        <li class="page-item">
            <a class="page-link" href="{href}" tabindex="-1">Previous</a>
        </li>
        '''
    else:
        previousPageLink = f'''
        <li class="page-item disabled">
            <a class="page-link" href="#" tabindex="-1">Previous</a>
        </li>
        '''

    if objects.has_next():
        href = f'?page={objects.next_page_number()}{query}'
        nextPageLink = f'''
        <li class="page-item">
            <a class="page-link" href="{href}" tabindex="-1">Next</a>
        </li>
        '''
    else:
        nextPageLink = f'''
        <li class="page-item disabled">
            <a class="page-link" href="#" tabindex="-1">Next</a>
        </li>
        '''

    pageNumberLinks = ''
    EITHER_SIDE_PAGE_LIMIT = 20
    pageRange = objects.paginator.page_range
    if pageRange.stop > EITHER_SIDE_PAGE_LIMIT:
        currentPage = int(request.GET.get('page') or 1)
        minRange = currentPage - EITHER_SIDE_PAGE_LIMIT // 2
        maxRange = currentPage + EITHER_SIDE_PAGE_LIMIT // 2

        if minRange <= 0:
            minRange = 1
        if maxRange > pageRange.stop:
            maxRange = pageRange.stop

        pageRange = range(minRange, maxRange)

    for pageNumber in pageRange:
        if objects.number == pageNumber:
            pageNumberLinks += f'''
                <li class="page-item active"><a class="page-link" href="#">{pageNumber}</a></li>
            '''
        else:
            href = f"?page={pageNumber}{query}"
            pageNumberLinks += f'''
                <li class="page-item"><a class="page-link" href="{href}">{pageNumber}</a></li>
            '''

    itemContent = f'''
    <div class="row">
        <div class="col-md-12" style="width: 1100px;">
            <nav aria-label="Page navigation example">
                <ul class="pagination justify-content-center">
                    {previousPageLink}
                    {pageNumberLinks}
                    {nextPageLink}
                </ul>
            </nav>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


class ProfileNavigator:

    def __init__(self, internalKey, query):
        self.internalKey = internalKey
        self.view = reverse('core:profile-view')
        self.query = query

    def getUrl(self):
        return f'{self.view}?page={self.query}'


@register.simple_tag
def renderProfileNavigationButtons(request):
    page = request.GET.get('page', 'address')

    navigations = [
        ProfileNavigator('Address', 'address'),
        ProfileNavigator('Notifications', 'notifications'),
        ProfileNavigator('Payment methods', 'paymentMethods'),
        ProfileNavigator('Settings', 'settings'),
    ]
    btnComponent = ''
    for button in navigations:
        btnClass = 'btn-primary' if page.casefold() == button.query.casefold() else 'btn-outline-primary'
        btnComponent += f'''
        <div class="col">
            <a type="button" href="{button.getUrl()}" class="btn {btnClass} btn-block">{button.internalKey}</a>
        </div>
        '''

    itemContent = f'''
    <div class="row">
    {btnComponent}
    </div>
    '''
    return mark_safe(itemContent)


def renderCountryDropdown(selected=None):
    countries = Address._meta.get_field('country').choices
    options = f'<option value="">Select your country</option>'

    for country in countries:
        isSelected = 'selected' if selected == country[0] else ''
        options += f'<option value="{country[0]}" {isSelected}>{country[1]}</option>'

    itemContent = f'''
    <select class="form-control" name="country" required>
        {options}
    </select>
    '''
    return mark_safe(itemContent)


def addressForm(instance=None):
    addressLine1 = instance.addressLine1 if instance else ''
    addressLine2 = instance.addressLine2 if instance else ''
    town = instance.town if instance else ''
    county = instance.county if instance else ''
    postcode = instance.postcode if instance else ''
    country = instance.country if instance else None
    isPrimary = 'checked' if instance and instance.isPrimary else ''
    itemContent = f'''
    <div class="form-group">
        <input type="text" class="form-control" name="addressLine1" placeholder="Address line 1" value="{addressLine1}" required>
    </div>
    <div class="form-group">
        <input type="text" class="form-control" name="addressLine2" placeholder="Address line 2" value="{addressLine2}">
    </div>
    <div class="form-row">
        <div class="form-group col-md-3">
            <input type="text" class="form-control" name="town" placeholder="Town" value="{town}" required>
        </div>
        <div class="form-group col-md-3">
            <input type="text" class="form-control" name="county" placeholder="County" value="{county}">
        </div>
        <div class="form-group col-md-3">
            <input type="text" class="form-control" name="postcode" placeholder="Postcode" value="{postcode}" required>
        </div>
        <div class="form-group col-md-3">
            {renderCountryDropdown(country)}
        </div>
    </div>
    <div class="form-group">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="isPrimary" style="height: 20px; width: 20px;" {isPrimary}>
            <label class="form-check-label" style="padding-top: 3px;margin-left: 10px;">
                Is this primary address?
            </label>
        </div>
    </div>
    '''
    return itemContent


def paymentMethodForm(instance=None):
    number = instance.getCardNumber if instance else ''
    name = instance.name if instance else ''
    expiration = instance.expiration.strftime("%Y-%m") if instance else ''
    cvv = instance.getCvvNumber if instance else ''
    isPrimary = 'checked' if instance and instance.isPrimary else ''
    minExpiryDate = timezone.now().strftime('%Y-%m')
    maxExpiryDate = f"{int(timezone.now().strftime('%Y')) + 5}-{timezone.now().strftime('%m')}"
    disabled = 'disabled' if instance else ''

    itemContent = f'''
    <div class="form-row">
        <div class="form-group col-md-6">
            <input type="text" class="form-control" name="number" placeholder="Card number" value="{number}"
                    maxlength="16" {disabled} required>
        </div>
        <div class="form-group col-md-6">
            <input type="text" class="form-control" name="name" placeholder="Name on card" value="{name}"
                    {disabled} required>
        </div>
    </div>
    <div class="form-row">
        <div class="form-group col-md-6">
            <input type="month" class="form-control" name="expiration" placeholder="Expiration date"
                    min="{minExpiryDate}" max="{maxExpiryDate}" value="{expiration}" {disabled} required>
        </div>
        <div class="form-group col-md-6">
            <input type="password" class="form-control" name="cvv" placeholder="CVV" maxlength="3" value="{cvv}"
                    {disabled} required>
        </div>
    </div>
    <div class="form-group">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="isPrimary" style="height: 20px; width: 20px;" {isPrimary}>
            <label class="form-check-label" style="padding-top: 3px;margin-left: 10px;">
                Should we use this as default payment method?
            </label>
        </div>
    </div>
    '''
    return itemContent


def addressModal(request):
    itemContent = f'''
        <div class="modal fade" id="address-modal" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <form class="modal-content" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                    <input type="hidden" name="ADD_ADDRESS">
                    <div class="modal-header">
                        <h5 class="modal-title">Add new address</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                    {addressForm()}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="submit" class="btn btn-primary">Add</button>
                    </div>
                </form>
            </div>
        </div>
        '''
    return itemContent


def paymentMethodModal(request):
    itemContent = f'''
        <div class="modal fade" id="payment-method-modal" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <form class="modal-content" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                    <input type="hidden" name="ADD_PAYMENT_METHOD">
                    <div class="modal-header">
                        <h5 class="modal-title">Add new payment method</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                    {paymentMethodForm()}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="submit" class="btn btn-primary">Add</button>
                    </div>
                </form>
            </div>
        </div>
        '''
    return itemContent


def renderProfileAddressComponent(request):
    addressList = Address.objects.filter(user=request.user).order_by('createdDttm')
    itemContent = f'''
    <div class="row float-right">
        {addressModal(request)}
        <button type="button" class="btn btn-dark" data-toggle="modal" data-target="#address-modal">Add</button>
    </div>
    <br></br>
    '''
    counter = 1

    for address in addressList:
        itemContent += f'''
        <div class="row">
            <form class="container" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                <input type="hidden" name="UPDATE_ADDRESS">
                <input type="hidden" name="address-id" value="{address.id}">
                <h3>Address {counter}</h3>
                {addressForm(address)}
                <button type="submit" class="btn btn-primary float-right">Update</button>
                <button class="btn btn-outline-danger float-right" style=" margin-right: 10px;"
                        onclick="deleteAddress({address.id})">Delete</button>
            </form>
        </div>
        <br>
        '''
        counter += 1
    return mark_safe(itemContent)


def renderPaymentMethodsComponent(request):
    itemContent = f'''
    <div class="row float-right">
        {paymentMethodModal(request)}
        <button type="button" class="btn btn-dark" data-toggle="modal" data-target="#payment-method-modal">Add</button>
    </div>
    <br></br>
    '''
    counter = 1

    for paymentMethod in PaymentMethod.objects.filter(user=request.user).order_by('createdDttm'):
        itemContent += f'''
        <div class="row">
            <form class="container" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                <input type="hidden" name="UPDATE_PAYMENT_METHOD">
                <input type="hidden" name="payment-method-id" value="{paymentMethod.id}">
                <h3>Payment method {counter}</h3>
                {paymentMethodForm(paymentMethod)}
                <button type="submit" class="btn btn-primary float-right">Update</button>
                <button class="btn btn-outline-danger float-right" style=" margin-right: 10px;"
                        onclick="deletePaymentMethod({paymentMethod.id})">Delete</button>
            </form>
        </div>
        <br>
        '''
        counter += 1
    return mark_safe(itemContent)


def renderAccountSettingsComponent(request):
    itemContent = f'''
    <div class="row">
        <form class="container" method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
            <input type="hidden" name="UPDATE_PERSONAL_SETTINGS">
            <h3>Personal details</h3>
            <div class="form-row">
                <div class="form-group col-md-6">
                    <input type="text" class="form-control" name="firstName" placeholder="First name"
                            value="{request.user.first_name}" required>
                </div>
                <div class="form-group col-md-6">
                    <input type="text" class="form-control" name="lastName" placeholder="Last name"
                            value="{request.user.last_name}" required>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group col-md-6">
                    <input type="email" class="form-control" name="email" placeholder="E-mail"
                            value="{request.user.email}" required>
                </div>
                <div class="form-group col-md-6">
                    <input type="password" class="form-control" name="password" placeholder="Password (Optional)">
                </div>
            </div>
            <button type="submit" class="btn btn-primary float-right">Update</button>
        </form>
    </div>
    <br></br>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderProfileNavigationContents(request):
    page = request.GET.get('page', 'address')
    itemContent = None

    if page.casefold() == 'address':
        itemContent = renderProfileAddressComponent(request)
    elif page.casefold() == 'paymentmethods':
        itemContent = renderPaymentMethodsComponent(request)
    elif page.casefold() == 'settings':
        itemContent = renderAccountSettingsComponent(request)

    return mark_safe(itemContent)
