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
    url(r'^trend_detection$', views.TrendDetectionView.as_view(), name='trend_detection'),
    url(r'^periodic_fluctuations$', views.PeriodicFluctuationsView.as_view(),
        name='periodic_fluctuations'),
    url(r'^auto_regressive$', views.AutoRegressiveView.as_view(), name='autoregressive'),
    url(r'^sampling$', views.SamplingFrequencyView.as_view(),
        name='sampling'),
    url(r'^bbox', views.BoundingBoxDataView.as_view(), name='map_data'),
    url(r'^timeseries/data$', views.TimeSeriesDataView.as_view(),
        name='timeseries_data'),
    url(r'^timeseries/uuid/(?P<uuid>[\w-]+)&(?P<start>[\w-]+)&(?P<end>[\w-]+)$',
        views.TimeSeriesStartPageView.as_view(),
        name='timeseries_start_end'),
    url(r'^timeseries/location_uuid/(?P<uuid>[\w-]+)&(?P<x_coord>[\w]+.[\w]+)&(?P<y_coord>[\w]+.[\w]+)$',
        views.TimeSeriesQueryView.as_view(),
        name='timeseries'),
    url(r'^map$', views.MapView.as_view(), name='map_'),
    url(r'^restart$', views.ReStartPageView.as_view(),
        name='restart'),
    url(r'^$', views.StartPageView.as_view(), name='startpage')
    # url(r'^something/',
    #     views.some_method,
    #     name="name_it"),
    # url(r'^something_else/$',
    #     views.SomeClassBasedView.as_view(),
    #     name='name_it_too'),
    ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
