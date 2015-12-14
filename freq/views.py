# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
import datetime
import json
import datetime as dt
from statistics import mean

from django.utils.encoding import uri_to_iri
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView

import pytz
from rest_framework.response import Response as RestResponse
from rest_framework.views import APIView
import pandas as pd

from freq import models
from freq.lizard_api_connector import GroundwaterLocations
from freq.lizard_api_connector import TimeSeries
from freq.lizard_api_connector import ApiError


def pd_timeseries_from_json(json_data, name=''):
    data_from_json = json.load(json_data)
    # store results in a dataframe
    dataframe = pd.DataFrame(data_from_json)
    index = pd.DatetimeIndex(dataframe[0], freq='infer', tz=pytz.utc)
    # build a timeseries object so we can compare it with other timeseries
    timeseries = pd.Series(dataframe[1].values, index=index, name=name)
    return timeseries


class BaseViewMixin(object):
    """Base view."""
    template_name = 'freq/base.html'
    title = _('GGMN - Global Groundwater Network')
    page_title = _('GGMN - Global Groundwater Network')
    menu_items = [
        ('Startpage', 'Back to Homepage', 'startpage'),
        ('Detection of Trends', 'Step trend or flat trend detection',
            'trend_detection'),
        ('Periodic Fluctuations', 'Estimate periodic fluctuations by harmonic '
            'analysis', 'periodic_fluctuations'),
        ('Autoregressive Model', 'Analyse the resulting, now stationary, time '
            'series with an autoregressive model (ARM)', 'autoregressive'),
        ('Sampling Frequency', 'Analysis and design of sampling frequency',
            'sampling'),
    ]
    active = ''
    tab_order = ['startpage', 'trend_detection', 'periodic_fluctuations',
                 'autoregressive', 'sampling']

    def get(self, request, *args, **kwargs):
        self.set_session()
        if request.GET.get('undo', False):
            self.undo()
        elif request.GET.get('redo', False):
            self.redo()
        return super().get(request, *args, **kwargs)

    def set_session(self):
        self.session[self.active] = self.session.get(self.active, {})

    def undo(self):
        remove = self.tab_order[self.last - 1]
        self.session['redo'][remove] = self.session[remove]
        if remove != 'startpage':
            self.session['disabled'][remove] = 'disabled'
        self.session[remove] = {}

    def redo(self):
        redo = self.tab_order[self.last]
        new_redo = self.session['redo'][redo]
        if new_redo:
            self.session['disabled'][redo] = ''
            self.session[redo] = new_redo

    def flush(self):
        self.session.update(self.default)
        del(self.session['disabled'])
        self.session['disabled'] = self.disabled

    @cached_property
    def default(self):
        return {
            'map_': {
                'center': [45, 0],
                'zoom': 3
            },
            'startpage': {
                'measurement_point': 'No Time Series Selected',
                'chart': 'hidden',
                'data': []
            },
            'trend_detection': {},
            'periodic_fluctuations': {},
            'autoregressive': {},
            'sampling': {},
        }

    @cached_property
    def disabled(self):
        try:
            return self.session['disabled']
        except KeyError:
            self.session['disabled'] = {
                'map_': '',
                'startpage': '',
                'trend_detection': 'disabled',
                'periodic_fluctuations': 'disabled',
                'autoregressive': 'disabled',
                'sampling': 'disabled'
            }
            return self.session['disabled']

    @cached_property
    def last(self):
        self.session['redo'] = self.session.get(
            'redo',
            {key: self.session.get(key, value) for key, value in
             self.default.items()}
        )
        for i, status in enumerate(self.tab_order):
            if self.session['disabled'][status] == 'disabled':
                break
        return i

    @cached_property
    def menu(self):
        return [
            (i + 1, title, description, link,
             self.disabled[link] if link != self.active else 'active')
            for i, (title, description, link) in enumerate(self.menu_items)
        ]

    @cached_property
    def show_error(self):
        if not 'error_message' in self.kwargs:
            self.error_message = ''
            return 'hidden'
        return ''

    @cached_property
    def measurement_point(self):
        return self.session['startpage'].get(
            'measurement_point', 'No Time Series Selected')

    @cached_property
    def selected_coords(self):
        return json.dumps([float(x) for x in self.session['startpage'].get(
            'selected_coords', [])])

    @cached_property
    def session(self):
        return self.request.session

    @cached_property
    def today(self):
        return dt.datetime.now().strftime('%d-%m-%Y')

    @cached_property
    def current(self):
        return self.active if self.active else 'map_'

    @property
    def start(self):
        start_old = self.session[self.current].get('start', self.today)
        return self.request.GET.get('start', start_old)

    @property
    def end(self):
        start_old = self.session[self.current].get('end', self.today)
        return self.request.GET.get('end', start_old)

    @property
    def time_window(self):
        return {'start': self.start + "T00:00:00Z",
                'end': self.end + "T00:00:00Z"}

    @property
    def center(self):
        try:
            return [float(x) for x in self.session['map_'].get('center', [45, 0])]
        except KeyError:
            return [45.0, 0.0]

    @property
    def zoom(self):
        try:
            return self.session['map_'].get('zoom', 3)
        except KeyError:
            return 3


class BaseView(BaseViewMixin, TemplateView):
    pass


class MapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'
    menu_items = []
    map_active = 'active'
    statistic_options = ('min', 'max', 'mean')

    @property
    def active_statistic(self):
        return self.session['map_'].get('active_statistic', 'mean')

    @property
    def statistics(self):
        return [s for s in self.statistic_options if s != self.active_statistic]


class StartPageView(BaseView):
    active = 'startpage'
    freq_active = 'active'
    template_name = 'freq/startpage.html'


class ReStartPageView(StartPageView):

    def get(self, request, *args, **kwargs):
        self.flush()
        return super().get(request, *args, **kwargs)


class TimeSeriesQueryView(StartPageView):

    def get(self, request, x_coord, y_coord, *args, **kwargs):
        print('in timeseries', kwargs['uuid'])
        kwargs['multiple_timeseries'] = False
        ts = TimeSeries()
        ts.location_uuid(kwargs['uuid'])
        request.session['startpage']['selected_coords'] = [x_coord, y_coord]
        request.session['map_']['center'] = [x_coord, y_coord]
        if len(ts.results) == 0:
            kwargs['error_message'] = 'No time series found for this ' \
                                      'location, please select another.'
        elif len(ts.results) == 1:
            request.session['startpage']['measurement_point'] = \
                "Meetpunt: " + ts.results[0]['name']
            request.session['disabled']['trend_detection'] = ''
            request.session['trend_detection'] = {'active': True}
        else:
            self.error_message = 'Multiple time series found for this ' \
                                 'location, please select one below.'
            self.multiple_timeseries = True
            self.timeseries = [
                (
                    x['location']['name'] + ' - ' + x['name'],
                    x['uuid'],
                    x['first_value_timestamp'],
                    x['last_value_timestamp']
                )
                for x in ts.results
            ]
        return super().get(request, *args, **kwargs)


class TimeSeriesStartPageView(StartPageView):

    def get(self, request, uuid, start, end, *args, **kwargs):
        ts = TimeSeries()
        ts.uuid(uuid, start, end)

        if len(ts.results) == 0:
            self.error_message = 'No time series found for this location, ' \
                                 'please select another.'
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
            request.session['trend_detection'] = {'active': True}
            request.session['startpage'].update(
                {
                    'start': start,
                    'end': end,
                    'uuid': uuid,
                    'data': data
                }
            )
            self.data = data
            self.chart = ''
        return super().get(request, *args, **kwargs)


class TrendDetectionView(BaseView):
    freq_active = 'active'
    active = 'trend_detection'
    template_name = 'freq/trend_detection.html'


class PeriodicFluctuationsView(BaseView):
    freq_active = 'active'
    active = 'periodic_fluctuations'
    template_name = 'freq/periodic_fluctuations.html'


class AutoRegressiveView(BaseView):
    freq_active = 'active'
    active = 'autoregressive'
    template_name = 'freq/autoregressive.html'


class SamplingFrequencyView(BaseView):
    freq_active = 'active'
    active = 'sampling'
    template_name = 'freq/sampling_frequency.html'


class BaseApiView(APIView, BaseViewMixin):
    pass


class BoundingBoxDataView(BaseApiView):

    def _lambda(self, x, *args):
        for arg in args:
            x = x.get(arg)
        return x

    def _divide_lambda(self, x, denominator, divisor):
        return self._lambda(x, denominator) / self._lambda(x, divisor)

    def min_max(self, lmbda, values, *args):
        return {'min': self._lambda(min(values, lmbda), *args),
                'max': self._lambda(max(values, lmbda), *args)}

    def get(self, request, *args, **kwargs):
        datatypes = request.GET.get('datatypes').split(',')
        try:
            response_dict = {
                "result": {
                    x: getattr(self, x) for x in datatypes},
                "error": ""
            }
        except ApiError:
            response_dict = {
                "result": {},
                "error": "Too many groundwater locations to show on map. "
                         "Please zoom in."
            }
        return RestResponse(response_dict)

    @property
    def locations(self):
        locations = GroundwaterLocations()
        locations.in_bbox(*self.coordinates)
        x = locations.coord_uuid_name()
        return x

    @property
    def timeseries(self):
        timeseries = TimeSeries()
        timeseries.from_bbox(*self.coordinates, **self.time_window)
        values = [{
                      'location_uuid': x['location']['unique_id'],
                      'values': x['events'][0],
                      'first': x['first_value_timestamp'],
                      'last': x['last_value_timestamp']
                  }
                  for x in timeseries.results]
        time = self.min_max(self._lambda, values, 'first')
        max_ = self.min_max(self._lambda, values, 'values', 'max')
        min_ = self.min_max(self._lambda, values, 'values', 'min')
        mean_ = self.min_max(self._divide_lambda, values,
                             ['values', 'sum'], ['values', 'count'])
        return {
            "values": values,
            "extremes": {
                "time": time,
                "max": max_,
                "min": min_,
                "mean": mean_,
            }
        }

    @cached_property
    def coordinates(self):
        coordinates = json.loads(self.request.GET.get('coordinates'))
        self.session['map_']['center'] = [
            mean([coordinates['SWlat'], coordinates['NElat']]),
            mean([coordinates['SWlng'], coordinates['NElng']])
        ]
        return [coordinates['SWlng'], coordinates['SWlat'],
                coordinates['NElng'], coordinates['NElat']]


class TimeSeriesDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        startpage = request.session['startpage']
        response_dict = {
            'data': startpage.get('data', []),
            'start': startpage.get('start', 0),
            'end': startpage.get('end', 0),
            'uuid': startpage.get('end', ''),
            'name': startpage.get('measurement_point', '')
        }
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
