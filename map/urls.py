from django.conf.urls import url
from django.contrib.auth.views import (logout, login)

from map import views

urlpatterns = [
	url(r'^$', login, name='login'),
	url(r'^logout/$', logout, name='logout'),
	# url(r'^register/$', views.register, name='register'),
	url(r'^map/$', views.mapView, name='map_view'),
	url(r'^form/$', views.formView, name='form_view'),
	url(r'^form/edita/(?P<pk>\w+)/$', views.formEditA, name='form_edit_a'),
	url(r'^form/editb/(?P<pk>\w+)/$', views.formEditB, name='form_edit_b'),
	url(r'^inspection/(?P<type>\w+)/$', views.inspectionView, name='inspection_view'),

	url(r'^api/form/removea/(?P<pk>\w+)/$', views.apiFormRemoveA, name='form_remove_a'),
	url(r'^api/form/removeb/(?P<pk>\w+)/$', views.apiFormRemoveB, name='form_remove_b'),
	url(r'^api/form/(?P<type>\w+)/$', views.apiForm, name='api_get_form'),
	url(r'^api/assetid/(?P<type>\w+)/$', views.apiCheckAssetId, name='api_assetid'),
	url(r'^api/geojson/$', views.apiGeoJson, name='api_geojson'),
	url(r'^api/upload/$', views.apiFileUpload, name='api_upload'),
	url(r'^api/download/$', views.apiFileDownload, name='api_download'),

	url(r'^api/inspection/(?P<type>\w+)/$', views.apiInspection, name='api_get_inspection'),
	url(r'^api/inspection-edit/(?P<type>\w+)/$', views.apiEditInspection, name='api_edit_inspection'),
	
	# url(r'^update-profile/(?P<pk>\d+)/$', views.update_profile, name='update_profile'),
]