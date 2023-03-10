from django import template
from django.urls import reverse

from core.models import Item
from core.utils.navigationBar import Icon, linkItem

register = template.Library()


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Home', reverse('core:index-view'), None),
        linkItem('New listing', reverse('core:new-listing'), None),
    ]

    if request.user.is_authenticated:
        cart = request.session.get('cart')
        if cart is not None and len(cart) > 0:
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
def itemConditionList():
    return Item._meta.get_field('condition').choices
