from django.urls import path, include
from mainapp import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

app_name = "mainapp"
urlpatterns = [
	path('', views.index, name='index'),
	path('login/', views.login, name='login'),
	path('signup/', views.signup, name='signup'),
	path('log_out/', views.log_out, name='log_out'),
	path('new_item/', views.new_item, name='new_item'),
	path('closedauction/', views.closedauction, name='closedauction'),
	path('update_profile/', views.update_profile, name='update_profile'),
	path('itempage.html/', views.itempage, name='itempage'),
	path('user_biddings/', views.user_biddings, name='user_biddings'),
]

#Should not have during production.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
