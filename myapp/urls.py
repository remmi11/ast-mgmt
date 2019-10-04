from django.conf.urls import include
from django.urls import path
from django.conf.urls import url
from django.contrib import admin

urlpatterns = [
    url(r'', include('map.urls')),
	path(r'admin/', admin.site.urls)
]