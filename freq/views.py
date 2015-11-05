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
from freq.lizard_api_connector import TimeSeries
from freq.lizard_api_connector import ApiError

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
    active = ''

    def disabled(self, request):
        try:
            return request.session['disabled']
        except KeyError:
            request.session['disabled'] = {
                'map_': '',
                'startpage': '',
                'trend_detection': 'disabled',
                'periodic_fluctuation': 'disabled',
                'autoregressive': 'disabled',
                'sampling': 'disabled'
            }
            return request.session['disabled']

    def get(self, request, *args, **kwargs):
        disabled = self.disabled(request)
        context = self.get_context_data(**kwargs)
        context['show_error'] = ''
        context['measurement_point'] = request.session.get('measurement_point',
                                                        'No Time Series Selected')
        context['menu'] = [
            (title, description, link, disabled[link] if link != self.active
            else 'active') for title, description,
            link in self.menu_items
        ]
        if not 'error_message' in kwargs:
            context['error_message'] = ''
            context['show_error']='hidden'
        return self.render_to_response(context)


class MapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'


class StartPageView(BaseView):
    active = 'startpage'
    template_name = 'freq/startpage.html'

    def get(self, request, *args, **kwargs):
        kwargs['multiple_timeseries'] = False
        if 'command' in kwargs and kwargs['command'] == 'restart':
            request.session.flush()
        if 'uuid' in kwargs:
            ts = TimeSeries()
            print(kwargs['uuid'])
            ts.location_uuid(kwargs['uuid'])
            print(len(ts.results))
            if len(ts.results) == 0:
                kwargs['error_message'] = 'No time series found for this ' \
                                          'location, please select another.'
            elif len(ts.results) == 1:
                request.session['measurement_point'] = "Meetpunt: " + \
                                                       ts.results[0]['name']
                request.session['disabled']['trend_detection'] = ''
            else:
                kwargs['error_message'] = 'Multiple time series found for ' \
                                          'this location, please select one ' \
                                          'below.'
                kwargs['multiple_timeseries'] = True
                kwargs['timeseries'] = [(x['location']['name'],
                                         x['location']['uuid'])
                                        for x in
                                        ts.results]
        return super().get(request, *args, **kwargs)


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
    template_name = 'freq/sampling_frequency.html'


class LocationsDataView(APIView):

    def post(self, request, *args, **kwargs):
        sw_lat = request.POST.get('SWlat')
        sw_lng = request.POST.get('SWlng')
        ne_lat = request.POST.get('NElat')
        ne_lng = request.POST.get('NElng')
        locations = GroundwaterLocations()
        try:
            locations.in_bbox(sw_lng, sw_lat, ne_lng, ne_lat)
            response_dict = {
                "locations": locations.coord_uuid_name(),
                "error": ""
            }
        except ApiError:
            response_dict = {
                "locations": [],
                "error": "Too many groundwater locations to show on map. "
                         "Please zoom in."
            }

        return RestResponse(response_dict)


class TimeSeriesDataView(APIView):

    def get(self, request, uuid, *args, **kwargs):
        print(uuid)
        return super().get(request, *args, **kwargs)

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
