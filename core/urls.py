from django.urls import path

from core import views
from core.api import *

app_name = "core"

urlpatterns = [
    path('', views.index, name='index-view'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('activate-account/<encodedId>/<token>', views.activateAccount, name='activate-account'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profileView, name='profile-view'),
    path('new-listing/', views.newListing, name='new-listing'),
    path('edit-listing/<int:pk>/', views.editListing, name='edit-listing'),
    path('user-listings/', views.userListings, name='user-listings'),
    path('user-purchases/', views.userPurchases, name='user-purchases'),
    path('user-bids/', views.userBids, name='user-bids'),
    path('item-bids/<int:pk>/', views.itemBids, name='item-bids'),
    path('item-view/<int:pk>/', views.itemView, name='item-view'),
    path('order-detail/<int:pk>/', views.orderDetailView, name='order-detail-view'),
    path('user/<int:pk>/items', views.itemsFromUser, name='items-from-user-view'),
    path('cart/', views.cartView, name='cart-view'),
]

urlpatterns += [
    path(
        'api/v1/addressObjectApiEventVersion1Component/',
        AddressObjectApiEventVersion1Component.as_view(),
        name='addressObjectApiEventVersion1Component'
    ),
]
