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
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('lizard_auth_client.urls')),
    url(r'^$', views.StartPageView.as_view(), name='startpage'),
    url(r'^trend_detection$', views.TrendDetectionView.as_view(), name='trend_detection'),
    url(r'^periodic_fluctuations$', views.PeriodicFluctuationsView.as_view(),
        name='periodic_fluctuations'),
    url(r'^auto_regressive$', views.AutoRegressiveView.as_view(), name='auto_regressive'),
    # url(r'^something/',
    #     views.some_method,
    #     name="name_it"),
    # url(r'^something_else/$',
    #     views.SomeClassBasedView.as_view(),
    #     name='name_it_too'),
    ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
