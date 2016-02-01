# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

from freq import views

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^', include('lizard_auth_client.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^trend_detection/$', views.TrendDetectionView.as_view(), name='trend_detection'),
    url(r'^periodic_fluctuations/$', views.PeriodicFluctuationsView.as_view(),
        name='periodic_fluctuations'),
    url(r'^autoregressive/$', views.AutoRegressiveView.as_view(), name='autoregressive'),
    url(r'^startpage_data/$', views.StartpageDataView.as_view(),
        name='startpage_data'),
    url(r'^trend_detection_data/$', views.TrendDataView.as_view(),
        name='trend_detection_data'),
    url(r'^periodic_fluctuations_data/$', views.FluctuationsDataView.as_view(),
        name='fluctuations_data'),
    url(r'^autoregressive_data/$', views.RegressiveDataView.as_view(),
        name='regressive_data'),
    url(r'^map/interpolation_limits/$',
        views.InterpolationLimits.as_view(), name='feature_info'),
    url(r'^map/feature_info/$',
        views.MapFeatureInfoView.as_view(), name='feature_info'),
    url(r'^map__data/$', views.MapDataView.as_view(),
        name='map__data'),
    url(r'^timeseries/data/$', views.TimeSeriesDataView.as_view(),
        name='timeseries_data'),
    url(r'^timeseries/uuid/(?P<uuid>[\w-]+)$',
        views.TimeSeriesByUUIDView.as_view(),
        name='timeseries_by_uuid'),
    url(r'^timeseries/location_uuid/$',
        views.TimeSeriesByLocationUUIDView.as_view(),
        name='timeseries_by_location_uuid'),
    url(r'^startpage/restart/$', views.ReStartPageView.as_view(),
        name='restart'),
    url(r'^startpage/$', views.StartPageView.as_view(), name='startpage'),
    url(r'^map/restart/$', views.MapRestartView.as_view(), name='flush'),
    url(r'^$', views.MapView.as_view(), name='map_')
    ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
