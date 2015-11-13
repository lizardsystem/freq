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
    tab_order = ['startpage', 'trend_detection', 'periodic_fluctuation',
                 'autoregressive', 'sampling']

    @property
    def default(self):
        return {
            'startpage': {
                'measurement_point': 'No Time Series Selected',
                'chart': 'hidden',
                'data': []
            },
            'trend_detection': {},
            'periodic_fluctuation': {},
            'autoregressive': {},
            'sampling': {},
        }

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

    def last(self, request):
        request.session['redo'] = request.session.get(
            'redo',
            {key: request.session.get(key, value) for key, value in
             self.default.items()}
        )
        for i, status in enumerate(self.tab_order):
            if request.session['disabled'][status] == 'disabled':
                break
        return i

    def undo(self, request):
        remove = self.tab_order[self.last(request) - 1]
        request.session['redo'][remove] = request.session[remove]
        if remove != 'startpage':
            request.session['disabled'][remove] = 'disabled'
        request.session[remove] = {}

    def redo(self, request):
        redo = self.tab_order[self.last(request)]
        new_redo = request.session['redo'][redo]
        if new_redo:
            request.session['disabled'][redo] = ''
            request.session[redo] = new_redo

    def flush(self, request):
        request.session.update(self.default)
        del(request.session['disabled'])
        request.session['disabled'] = self.disabled(request)

    def get(self, request, *args, **kwargs):
        if request.GET.get('undo', False):
            self.undo(request)
        elif request.GET.get('redo', False):
            self.redo(request)
        disabled = self.disabled(request)
        context = self.get_context_data(**kwargs)
        context['show_error'] = ''
        context['measurement_point'] = request.session['startpage'].get(
            'measurement_point', 'No Time Series Selected')
        context['menu'] = [
            (title, description, link, disabled[link] if link != self.active
            else 'active') for title, description,
            link in self.menu_items
        ]
        if not 'error_message' in kwargs:
            context['error_message'] = ''
            context['show_error']='hidden'
        context['selected_coords'] = json.dumps([float(x) for x
                                                 in request.session[
                                                     'startpage'].get(
            'selected_coords', [])])
        return self.render_to_response(context)

    def set_session(self, request):
        request.session[self.active] = request.session.get(self.active, {})


class MapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'


class StartPageView(BaseView):
    active = 'startpage'
    template_name = 'freq/startpage.html'

    def get(self, request, *args, **kwargs):
        self.set_session(request)
        return super().get(request, *args, **kwargs)


class ReStartPageView(StartPageView):

    def get(self, request, *args, **kwargs):
        self.flush(request)
        self.set_session(request)
        return super().get(request, *args, **kwargs)


class TimeSeriesQueryView(StartPageView):

    def get(self, request, x_coord, y_coord, *args, **kwargs):
        kwargs['multiple_timeseries'] = False
        ts = TimeSeries()
        ts.location_uuid(kwargs['uuid'])
        request.session['startpage']['selected_coords'] = [x_coord, y_coord]
        if len(ts.results) == 0:
            kwargs['error_message'] = 'No time series found for this ' \
                                      'location, please select another.'
        elif len(ts.results) == 1:
            request.session['startpage']['measurement_point'] = \
                "Meetpunt: " + ts.results[0]['name']
            request.session['disabled']['trend_detection'] = ''
            request.session['trend_detection'] = {'active':True}
        else:
            kwargs['error_message'] = 'Multiple time series found for ' \
                                      'this location, please select one ' \
                                      'below.'
            kwargs['multiple_timeseries'] = True
            kwargs['timeseries'] = [
                (
                    x['location']['name'] + ' - ' + x['name'],
                    x['uuid'],
                    x['first_value_timestamp'],
                    x['last_value_timestamp']
                )
                for x in ts.results]
        return super().get(request, *args, **kwargs)


class TimeSeriesStartPageView(StartPageView):

    def get(self, request, uuid, start, end, *args, **kwargs):
        ts = TimeSeries()
        ts.uuid(uuid, start, end)

        if len(ts.results) == 0:
            kwargs['error_message'] = 'No time series found for this ' \
                                      'location, please select another.'
        else:
            data = [{'y': x['max'], 'x': x['timestamp']}
                             for x in ts.results[0]['events']]
            data = [{
                'values': data,
                'key': 'Groundwaterlevels (m)',
                'color': '#1abc9c'
            }]
            request.session['startpage']['measurement_point'] = \
                "Meetpunt: " + ts.results[0]['location']['name']
            request.session['disabled']['trend_detection'] = ''
            request.session['trend_detection'] = {'active':True}
            request.session['startpage'].update(
                {
                    'start': start,
                    'end': end,
                    'uuid': uuid,
                    'data': data
                }
            )
            kwargs['data'] = data
            kwargs['chart'] = ''
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

    def get(self, request, *args, **kwargs):
        startpage = request.session['startpage']
        response_dict = {
            'data': startpage.get('data', []),
            'start': startpage.get('start', 0),
            'end': startpage.get('end', 0),
            'uuid': startpage.get('end', ''),
            'name': startpage.get('measurement_point', '')
        }
        print(response_dict)
        return RestResponse(response_dict)

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
