# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
import datetime
import json

from django.utils.encoding import uri_to_iri
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
import pytz
from rest_framework.response import Response as RestResponse
from rest_framework.views import APIView

from freq import models
from freq.lizard_api_connector import GroundwaterLocations


disabled = {
    'map_': '',
    'startpage': '',
    'trend_detection': 'disabled',
    'periodic_fluctuation': 'disabled',
    'autoregressive': 'disabled',
    'sampling': 'disabled'
}


class BaseView(TemplateView):
    """Base view."""
    template_name = 'freq/base.html'
    title = _('FREQ - frequency analysis of groundwater measurements')
    page_title = _('FREQ - frequency analysis groundwater measurements')
    menu_items = [
        ('Map', 'Full page map', 'map_'),
        ('Startpage', 'Back to Homepage', 'startpage'),
        ('Detection of Trends', 'Step trend or flat trend detection',
            'trend_detection'),
        ('Periodic Fluctuations', 'Estimate periodic fluctuations by harmonic '
            'analysis', 'periodic_fluctuation'),
        ('Autoregressive Model', 'Analyse the resulting, now stationary, time '
            'series with an autoregressive model (ARM)', 'autoregressive'),
        ('Sampling Frequency', 'Analysis and design of sampling frequency',
            'sampling'),
    ]
    measurement_point = 'No Time Series Selected'
    active = ''

    @property
    def menu(self):
        return [
            (title, description, link, disabled[link] if link != self.active
            else 'active') for title, description,
            link in self.menu_items
        ]


class MapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'


class StartPageView(BaseView):
    active = 'startpage'
    template_name = 'freq/startpage.html'


class TrendDetectionView(BaseView):
    active = 'trend_detection'
    template_name = 'freq/trend_detection.html'


class PeriodicFluctuationsView(BaseView):
    active = 'periodic_fluctuation'
    template_name = 'freq/periodic_fluctuations.html'


class AutoRegressiveView(BaseView):
    active = 'autoregressive'
    template_name = 'freq/autoregressive.html'


class SamplingFrequencyView(BaseView):
    active = 'sampling'
    template_name = 'freq/sampling.html'


class LocationsDataView(APIView):

    def post(self, request, *args, **kwargs):
        sw_lat = request.POST.get('SWlat')
        sw_lng = request.POST.get('SWlng')
        ne_lat = request.POST.get('NElat')
        ne_lng = request.POST.get('NElng')
        locations = GroundwaterLocations()
        locations.in_bbox(sw_lng, sw_lat, ne_lng, ne_lat)
        response_dict = {"locations": locations.coord_uuid_name()}
        print(response_dict)
        return RestResponse(response_dict)


class TimeSeriesView(TemplateView):
    template_name = 'freq/startpage.html'

    def get(self, request, uuid, *args, **kwargs):
        print(uuid)


class TimeSeriesDataView(APIView):

    def get(self, request, uuid, *args, **kwargs):
        print(uuid)

    # JS_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    #
    # def datetime_to_js(self, dt):
    #     if dt is not None:
    #         return (dt - self.JS_EPOCH).total_seconds() * 1000
    #
    # def series_to_js(self, pdseries):
    #     # bfill because sometimes first element is a NaN
    #     pdseries = pdseries.fillna(method='bfill')
    #     return [(self.datetime_to_js(dt), float_or_none(value))
    #             for dt, value in pdseries.iterkv()]
