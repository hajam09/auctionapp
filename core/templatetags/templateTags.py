from django import template
from django.db.models import Sum, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.models import Item, Bid, Image
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
                    linkItem('My listings', reverse('core:user-listings'), Icon('', 'fas fa-sign-out-alt', '15')),
                    linkItem('My purchases', reverse('core:user-purchases'), Icon('', 'fas fa-sign-out-alt', '15')),
                    linkItem('My Bidding\'s', reverse('core:user-bids'), Icon('', 'fas fa-sign-out-alt', '15')),
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


@register.filter
def itemStatus(item):
    if item.buyer is not None:
        return "SOLD"
    elif item.type == Item.Type.AUCTION and item.buyer is not None and item.isExpired():
        return "SOLD"
    elif item.type == Item.Type.AUCTION and item.buyer is None and item.isExpired():
        "NOT SOLD"
    return "LISTED"


@register.filter
def userBidStatus(bid):
    if bid[1] > bid[3]:
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
            <a class="btn btn-outline-dark mt-3" href="{reverse('core:edit-listing', kwargs={'pk': item.pk})}" role="button">
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
    elif item.type == Item.Type.BUY_IT_NOW and item.id not in userCart:
        return mark_safe(
            f'''
            <a class="btn btn-outline-primary mt-3"
                href="{reverse('core:cart-view')}?function=add&id={item.id}"
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


@register.simple_tag
def renderItemCatalogue(request, item, showSeller):
    showSeller = eval(showSeller)
    itemExpireDttm = f'''
    <li class="list-inline-item">
        <span class="text-muted" data-abc="true">Expires at {item.expireDate.strftime('%B %d, %Y %H:%M:%S')}</span>
    </li>
    ''' if item.type == Item.Type.AUCTION else '<span></span>'

    sellerLine = '<span></span>'
    if showSeller:
        sellerLine = f'''
        <li class="list-inline-item">
            All items from
            <a href="{reverse('core:items-from-user-view', kwargs={'pk': item.seller.pk})}" data-abc="true">{item.seller.get_short_name()}</a>
        </li>
        '''

    averageRating = item.itemReview.aggregate(avg=Avg('rating')).get('avg')
    rating = generateStarRatingFromFloat(averageRating) if averageRating else ''

    itemDelivery = f'''
        <p class="text-secondary">£{item.deliveryCharge} postage</p>
        ''' if item.deliveryCharge else f'<p class="text-success">Free shipping</p>'

    itemContent = f'''
        <div class="card card-body mt-3">
            <div class="media align-items-center align-items-lg-start text-center text-lg-left flex-column flex-lg-row">
                <div class="mr-2 mb-3 mb-lg-0">
                    <img src="https://cdn-thumbs.imagevenue.com/09/85/ad/ME1573QH_t.jpg" width="150" height="150" alt="">
                </div>
                <div class="media-body">
                    <h6 class="media-title font-weight-semibold">
                        <a href="{reverse('core:item-view', kwargs={'pk': item.pk})}"
                           data-abc="true">{item.title}</a>
                    </h6>
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
                </div>
                <div class="mt-3 mt-lg-0 ml-lg-3 text-center">
                    <h3 class="mb-0 font-weight-semibold">£{item.price}</h3>
                    <div>
                        {rating}
                    </div>
                    <div class="text-muted">{item.itemReview.count()} reviews</div>
                    <div class="text-muted">{itemDelivery}</div>
                    {itemCartButton(request, item)}
                </div>
            </div>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemCatalogueWithOrderFurtherDetailsComponent(order, orderStatusList):
    orderStatus = next((os for os in orderStatusList if os.order == order), None)
    itemContent = f'''
        <div class="card card-body mt-3">
            <div class="media align-items-center align-items-lg-start text-center text-lg-left flex-column flex-lg-row">
                <div class="mr-2 mb-3 mb-lg-0">
                    <img src="https://cdn-thumbs.imagevenue.com/09/85/ad/ME1573QH_t.jpg" width="150"
                         height="150" alt="">
                </div>
                <div class="media-body">
                    <h6 class="media-title font-weight-semibold">
                        <a href="/item-view/1/" data-abc="true">{order.item.title}</a>
                    </h6>
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
                            <a href="/user/1/items"
                               data-abc="true">{order.item.seller.get_short_name()}</a>
                        </li>
                    </ul>
                </div>
                <div class="mt-3 mt-lg-0 ml-lg-3 text-center">
                    <ul class="no-bullets" style="list-style-type: none; margin: 0; padding: 0;">
                        <li>
                            <a class="btn btn-primary mt-3" style="width: 100%;" href="/cart/?function=add&amp;id=1"
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
                                <a class="dropdown-item" href="#">Contact seller</a>
                                <a class="dropdown-item" href="#">Return this item</a>
                                <a class="dropdown-item" href="#">leave feedback</a>
                                <a class="dropdown-item" href="#">I didn't receive it</a>
                                <a class="dropdown-item" href="#">Add note</a>
                                <a class="dropdown-item" href="#">Hide order</a>
                            </div>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderItemCartProductCatalogue(item):
    itemContent = f'''
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div class="d-flex flex-row align-items-center">
                        <div>
                            <img src="https://mdbcdn.b-cdn.net/img/Photos/new-templates/bootstrap-shopping-carts/img1.webp"
                                class="img-fluid rounded-3" alt="Shopping item"
                                style="width: 65px;">
                        </div>
                        <div class="ms-3">
                            <h5>{item.title}</h5>
                            <p class="small mb-0">{f'{item.description[:70]}...' if len(item.description) > 70 else item.description}</p>
                        </div>
                    </div>
                    <div class="d-flex flex-row align-items-center">
                        <div style="width: 80px;">
                            <h5 class="mb-0">£{item.price}</h5>
                        </div>
                        <a href="{reverse('core:cart-view')}?function=remove&id={item.id}" style="color: #cecece;">
                            <i class="fas fa-trash-alt"></i></a>
                    </div>
                </div>
            </div>
        </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderCardDetailsInputComponent(itemList):
    totalPrice = '{:,.2f}'.format(itemList.aggregate(price=Sum('price')).get('price') if itemList.count() > 0 else 0)
    itemContent = f'''
    <div class="card bg-light rounded-3">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h5 class="mb-0">Card details</h5>
            </div>
            <p class="small mb-2">Card type</p>
            <a href="#" type="submit"><i class="fab fa-cc-mastercard fa-2x me-2"></i></a>
            <a href="#" type="submit"><i class="fab fa-cc-visa fa-2x me-2"></i></a>
            <a href="#" type="submit"><i class="fab fa-cc-amex fa-2x me-2"></i></a>
            <a href="#" type="submit"><i class="fab fa-cc-paypal fa-2x"></i></a>
            <form class="mt-4">
                <div class="form-outline form-white mb-4">
                    <input type="text" id="typeName"
                           class="form-control form-control-lg" siez="17"
                           placeholder="Cardholder's Name"/>
                    <label class="form-label" for="typeName">Cardholder's Name</label>
                </div>
                <div class="form-outline form-white mb-4">
                    <input type="text" id="typeText"
                           class="form-control form-control-lg" siez="17"
                           placeholder="1234 5678 9012 3457" minlength="19"
                           maxlength="19"/>
                    <label class="form-label" for="typeText">Card Number</label>
                </div>
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="form-outline form-white">
                            <input type="text" id="typeExp"
                                   class="form-control form-control-lg"
                                   placeholder="MM/YYYY" size="7" id="exp" minlength="7"
                                   maxlength="7"/>
                            <label class="form-label" for="typeExp">Expiration</label>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-outline form-white">
                            <input type="password" id="typeText"
                                   class="form-control form-control-lg"
                                   placeholder="&#9679;&#9679;&#9679;" size="1"
                                   minlength="3" maxlength="3"/>
                            <label class="form-label" for="typeText">CVV</label>
                        </div>
                    </div>
                </div>
            </form>
            <hr class="my-4">
            <div class="d-flex justify-content-between">
                <p class="mb-2">Subtotal</p>
                <p class="mb-2">£{totalPrice}</p>
            </div>
            <div class="d-flex justify-content-between">
                <p class="mb-2">Shipping</p>
                <p class="mb-2">£0.00</p>
            </div>
            <div class="d-flex justify-content-between mb-4">
                <p class="mb-2">Total(Incl. taxes)</p>
                <p class="mb-2">£{totalPrice}</p>
            </div>
            <button type="submit" class="btn btn-info btn-block btn-lg">
                <div class="d-flex justify-content-between">
                    <span>£{totalPrice}</span>
                    <span>Checkout <i
                            class="fas fa-long-arrow-alt-right ms-2"></i></span>
                </div>
            </button>
        </div>
    </div>
    '''
    return mark_safe(itemContent)


@register.simple_tag
def renderUserListingTable(item):
    viewBiddingButton = '<span></span>'
    if item.type == Item.Type.AUCTION:
        viewBiddingButton = f'''<a class="btn btn-outline-secondary btn-sm" href="{reverse('core:item-bids', kwargs={'pk': item.pk})}" role="button">View Bidding's</a>'''''

    itemContent = f'''
        <tr>
            <th scope="row">{item.id}</th>
            <td>{item.title}</td>
            <td>
            <span class="badge badge-{'primary' if item.type == Item.Type.BUY_IT_NOW else 'secondary'}">{item.get_type_display()}</span>
            </td>
            <td>£{item.price}</td>
            <td>{itemStatus(item)}</td>
            <td>
                <a class="btn btn-outline-primary btn-sm" href="{reverse('core:item-view', kwargs={'pk': item.pk})}"
                   role="button">View</a>
                <a class="btn btn-outline-dark btn-sm" href="{reverse('core:edit-listing', kwargs={'pk': item.pk})}"
                   role="button">Edit</a>
                <a class="btn btn-outline-danger btn-sm" href="{reverse('core:user-listings')}?function=delete&item={item.pk}"
                   role="button">Delete</a>
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
def renderUserBidsTable(bid):
    viewBiddingButton = '<span></span>'
    if bid[2] == Item.Type.AUCTION:
        viewBiddingButton = f'''
        <a class="btn btn-outline-secondary btn-sm" href="{reverse('core:item-bids', kwargs={'pk': bid[0]})}" role="button">View Bidding's</a>
        '''

    itemContent = f'''
        <tr>
            <th scope="row">{bid[0]}</th>
            <td>£{bid[3]}</td>
            <td>{bid[1]}</td>
            <td>{userBidStatus(bid)}</td>
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
                <input class="form-control" type="number" name="bidAmount" min={currentPrice} step=".1" style="max-width: 18%;">
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

    averageRating = item.itemReview.aggregate(avg=Avg('rating')).get('avg')
    rating = generateStarRatingFromFloat(averageRating) if averageRating else 'No ratings yet.'

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
                    <dd class="col-sm-10">{item.stock} available</dd>

                    <dd class="col-sm-2">Postage:</dd>
                    <dd class="col-sm-10">{'£' + str(item.deliveryCharge) if item.deliveryCharge else 'Free postage'}</dd>

                    <dd class="col-sm-2">Returns:</dd>
                    <dd class="col-sm-10">TODO</dd>
                </dl>
                <div class="card bg-light">
                    <div class="card-body">
                        <form method="post">
                            <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE')}">
                            {getItemQuantityComponent(item.stock) if item.type == Item.Type.BUY_IT_NOW else getItemAuctionComponent(currentPrice)}
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    return mark_safe(itemContent)
