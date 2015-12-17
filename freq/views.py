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
from freq.lizard_api_connector import GroundwaterTimeSeries
from freq.lizard_api_connector import ApiError


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
        # ('Sampling Frequency', 'Analysis and design of sampling frequency',
        #     'sampling'),
    ]
    active = ''
    tab_order = ['startpage', 'trend_detection', 'periodic_fluctuations',
                 'autoregressive']
    default_state = {
        'map_': {
            'center': [45.0, 0.0],
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
        'disabled': {
                'map_': '',
                'startpage': '',
                'trend_detection': 'disabled',
                'periodic_fluctuations': 'disabled',
                'autoregressive': 'disabled',
        }
    }

    def set_session(self):
        for key in self.default_state.keys():
            self.session[key] = self.session.get(key, self.default_state[key])

    def undo(self):
        remove = self.tab_order[self.last - 1]
        self.redo_state[remove] = self.session[remove]
        if remove != 'startpage':
            self.disabled_state[remove] = 'disabled'
        self.session[remove] = {}

    def redo(self):
        redo = self.tab_order[self.last]
        new_redo = self.redo_state[redo]
        if new_redo:
            self.disabled_state[redo] = ''
            self.session[redo] = new_redo

    def flush(self):
        self.session.update(self.default_state)

    @cached_property
    def map_state(self):
        return self.session['map_']

    @cached_property
    def startpage_state(self):
        return self.session['startpage']

    @cached_property
    def autoregressive_state(self):
        return self.session['autoregressive']

    @cached_property
    def periodic_fluctuations_state(self):
        return self.session['periodic_fluctuations']

    @cached_property
    def trend_detection_state(self):
        return self.session['trend_detection']

    @cached_property
    def disabled_state(self):
        return self.session['disabled']

    @cached_property
    def undo_state(self):
        return self.session['undo']

    @cached_property
    def redo_state(self):
        return self.session['redo']

    @cached_property
    def last(self):
        self.session['redo'] = self.session.get(
            'redo',
            {key: self.session.get(key, value) for key, value in
             self.default_state.items()}
        )
        for i, status in enumerate(self.tab_order):
            if self.disabled_state[status] == 'disabled':
                break
        return i

    @cached_property
    def menu(self):
        return [
            (i + 1, title, description, link,
             self.disabled_state[link] if link != self.active else 'active')
            for i, (title, description, link) in enumerate(self.menu_items)
        ]

    @cached_property
    def show_error(self):
        print('show error????')
        if not 'error_message' in self.kwargs:
            self.error_message = ''
            return 'hidden'
        return ''

    @cached_property
    def measurement_point(self):
        return self.startpage_state.get(
            'measurement_point', 'No Time Series Selected')

    @cached_property
    def selected_coords(self):
        return json.dumps([float(x) for x in self.startpage_state.get(
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
        print(self.map_state)
        try:
            return [float(x) for x in self.map_state.get('center', [45, 0])]
        except KeyError:
            return [45.0, 0.0]

    @property
    def zoom(self):
        try:
            return self.map_state.get('zoom', 3)
        except KeyError:
            return 3

    @property
    def freq_icon_size(self):
        if self.active == 'map_':
            return "glyphicon-sm"
        else:
            return ""

    @property
    def map_icon_size(self):
        if self.active != 'map_':
            return "glyphicon-sm"
        else:
            return ""

    @cached_property
    def timeseries(self):
        ts = GroundwaterTimeSeries()
        ts.uuid(self.startpage_state['uuid'], self.startpage_state['start'],
                self.startpage_state['end'])

        if len(ts.results) == 0:
            self.error_message = 'No time series found for this location, ' \
                                 'please select another.'
        else:
            data = [{'y': x['max'], 'x': x['timestamp']}
                             for x in ts.results[0]['events']]
            self.data = {
                'values': data,
                'key': 'Groundwaterlevels (m)',
                'color': '#1abc9c'
            }

        return self.data



class FreqTemplateView(TemplateView):

    def dispatch(self, *args, **kwargs):
        self.set_session()
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.GET.get('undo', False):
            self.undo()
        elif request.GET.get('redo', False):
            self.redo()
        return super().get(request, *args, **kwargs)


class BaseView(BaseViewMixin, FreqTemplateView):
    pass


class MapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'
    menu_items = []
    map_active = 'active'
    statistic_options = ('min', 'max', 'mean')

    @property
    def active_statistic(self):
        return self.map_state.get('active_statistic', 'mean')

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


class TimeSeriesByLocationUUIDView(StartPageView):
    error_message = ''

    @cached_property
    def timeseries(self):
        ts = GroundwaterTimeSeries()
        ts.location_uuid(self.uuid)
        return ts.results

    @cached_property
    def multiple_timeseries(self):
        return len(self.timeseries) > 1

    @cached_property
    def error_message(self):
        if self.multiple_timeseries:
            return 'Multiple time series found for this location, please ' \
                   'select one below.'
        elif len(self.timeseries) == 1:
            return 'No time series found for this location, please select ' \
                   'another.'
        return ''

    @property
    def timeseries_selection(self):
        if self.multiple_timeseries:
            return [
                (
                    x['location']['name'] + ' - ' + x['name'],
                    x['uuid'],
                    x['first_value_timestamp'],
                    x['last_value_timestamp']
                )
                for x in self.timeseries
            ]
        elif len(self.timeseries) == 1:
            result = self.timeseries[0]
            self.session['startpage']['measurement_point'] = \
                "Meetpunt: " + result['name']
            self.disabled_state['trend_detection'] = ''
            self.trend_detection_state.update({'active': True})
            self.startpage_state.update(
                {
                    'start': result['first_value_timestamp'],
                    'end': result['last_value_timestamp'],
                    'uuid': result['uuid']
                }
            )
        return []

    @cached_property
    def uuid(self):
        return self.request.GET['uuid']

    @cached_property
    def coordinates(self):
        return [self.request.GET['x_coord'], self.request.GET['y_coord']]

    def get(self, request, *args, **kwargs):
        self.startpage_state['selected_coords'] = self.coordinates
        self.map_state['center'] = self.coordinates
        return super().get(request, *args, **kwargs)


class TimeSeriesByUUIDView(StartPageView):

    def get(self, request, uuid, *args, **kwargs):
        self.startpage_state.update(
            {
                'measurement_point': "Meetpunt: " + self.request.GET['name'],
                'start': self.request.GET['start'],
                'end': self.request.GET['end'],
                'uuid': uuid
            }
        )
        self.disabled_state['trend_detection'] = ''
        self.trend_detection_state.update({'active': True})
        self.chart = ''
        return super().get(request, *args, **kwargs)


class TrendDetectionView(BaseView):
    freq_active = 'active'
    active = 'trend_detection'
    template_name = 'freq/trend_detection.html'
    spinner_heading = 'Alpha (significance)'
    spinner_title = "alpha (significance of the t-test for changes in the " \
                    "mean (0-1))"
    spinner_min = 0.01
    spinner_max = 0.99
    spinner_step = 0.01
    spinner_precision = 2

    dropdown_heading = "Trend type"
    dropdown_selected = "Step trend"
    dropdown_options = [
        ("Linear trend", "#")
    ]

    @property
    def spinner_value(self):
        return self.trend_detection_state.get('spinner_value', "0.95")


class PeriodicFluctuationsView(BaseView):
    freq_active = 'active'
    active = 'periodic_fluctuations'
    template_name = 'freq/periodic_fluctuations.html'
    spinner_heading = 'Number of harmonics'
    spinner_title = "Number of harmonics to be removed from the series"
    spinner_min = 0
    spinner_step = 1
    spinner_precision = 0

    @property
    def spinner_max(self):
        return int(self.length / 2)

    @property
    def length(self):
        return 20  # TODO

    @property
    def spinner_value(self):
        return self.trend_detection_state.get('spinner_value', "0")


class AutoRegressiveView(BaseView):
    freq_active = 'active'
    active = 'autoregressive'
    template_name = 'freq/autoregressive.html'
    spinner_heading = 'Number of periods'
    spinner_title = "Number of periods used in the training of the autoregressive model"
    spinner_min = 0
    spinner_step = 1
    spinner_precision = 0

    @property
    def spinner_max(self):
        return int(0.3 * self.length)

    @property
    def length(self):
        return 20  # TODO


class SamplingFrequencyView(BaseView):
    freq_active = 'active'
    active = 'sampling'
    template_name = 'freq/sampling_frequency.html'


class BaseApiView(BaseViewMixin, APIView):
    JS_EPOCH = dt.datetime(1970, 1, 1, tzinfo=pytz.utc)

    def pd_timeseries_from_json(json_data, name=''):
        data_from_json = json.load(json_data)
        # store results in a dataframe
        dataframe = pd.DataFrame(data_from_json)
        index = pd.DatetimeIndex(dataframe[0], freq='infer', tz=pytz.utc)
        # build a timeseries object so we can compare it with other timeseries
        timeseries = pd.Series(dataframe[1].values, index=index, name=name)
        return timeseries

    @property
    def button(self):
        return self.request.GET.get('button', '')

    @property
    def value(self):
        return self.request.GET.get('value', '')

    @property
    def pd_timeseries(self):
        return self.pd_timeseries_from_json(self.timeseries)

    def datetime_to_js(self, date_time):
        if date_time is not None:
            return (date_time - self.JS_EPOCH).total_seconds() * 1000

    def js_to_datetime(self, date_time):
        if date_time is not None:
            return self.JS_EPOCH + dt.timedelta(seconds=date_time/1000)


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
        timeseries = GroundwaterTimeSeries()
        timeseries.from_bbox(*self.coordinates, **self.time_window)
        values = [{
                      'location_uuid': x['location']['unique_id'],
                      'values': x['events'][0],
                      'start': x['first_value_timestamp'],
                      'end': x['last_value_timestamp']
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
        self.map_state['center'] = [
            mean([coordinates['SWlat'], coordinates['NElat']]),
            mean([coordinates['SWlng'], coordinates['NElng']])
        ]
        return [coordinates['SWlng'], coordinates['SWlat'],
                coordinates['NElng'], coordinates['NElat']]


class TimeSeriesDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        print(self.timeseries)
        response_dict = {
            'data': self.timeseries,
            'start': self.startpage_state.get('start', 0),
            'end': self.startpage_state.get('end', 0),
            'uuid': self.startpage_state.get('uuid', ''),
            'name': self.startpage_state.get('measurement_point', '')
        }
        return RestResponse(response_dict)




class StartpageDataView(BaseApiView):
    active = 'startpage'

    def get(self, request, *args, **kwargs):
        print(self.button)
        print(json.loads(self.value))
        return RestResponse({})


class TrendDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        print(self.button)
        print(json.loads(self.value))
        return RestResponse({})


class FluctuationsDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        print(self.button)
        print(json.loads(self.value))
        return RestResponse({})


class RegressiveDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        print(self.button)
        print(json.loads(self.value))
        return RestResponse({})



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
