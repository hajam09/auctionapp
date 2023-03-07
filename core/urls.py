from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path('', views.index, name='index-view'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('activate-account/<encodedId>/<token>', views.activateAccount, name='activate-account'),
    path('logout/', views.logout, name='logout'),
    path('new-listing/', views.newListing, name='new-listing'),
    path('user-listings/', views.userListings, name='user-listings'),
    path('user-purchases/', views.userPurchases, name='user-purchases'),
    path('user-bids/', views.userBids, name='user-bids'),
    path('item-bids/<int:pk>/', views.itemBids, name='item-bids'),
    path('item-view/<int:pk>/', views.itemView, name='item-view'),
]
