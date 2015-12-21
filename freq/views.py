# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
import copy
import datetime
import json
import datetime as dt
from pprint import pprint
from statistics import mean
from time import sleep   # TODO: VERY UGLY HACK

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


def today():
    return dt.datetime.now().strftime('%d-%m-%Y')

DEFAULT_STATE = {
    'map_': {
        'center': [45.0, 0.0],
        'zoom': 3
    },
    'startpage': {
        'chart': 'hidden',
        'datepicker': {'start': '1-1-1900', 'end': today()},
        'end_js': 1000000000000,
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'measurement_point': 'No Time Series Selected',
        'selected_coords': [],
        'start_js': 0,
        'uuid': 'EMPTY',
    },
    'trend_detection': {
        'active': False,
        'datepicker': {'start': '1-1-1900', 'end': today()},
        'dropdown': {'value': 'Linear Trend'},
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'spinner': {'value': 0.95},
    },
    'periodic_fluctuations': {
        'spinner': {'value': 0},
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'autoregressive': {
        'spinner': {'value': 0},
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'disabled': {
            'startpage': 'enabled',
            'trend_detection': 'disabled',
            'periodic_fluctuations': 'disabled',
            'autoregressive': 'disabled',
    },
}

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

    # ------------------------------------------------------------------------ #
    ### Session handling

    # def dispatch(self, *args, **kwargs):
    #     print('\n\n\nIN {}'.format(type(self).__name__))
    #     pprint(dict(self.request.session))
    #     return super().dispatch(*args, **kwargs)

    def instantiate_session(self):
        print('INSTANTIATING!')
        self.request.session['session_is_set'] = True
        default = copy.deepcopy(DEFAULT_STATE)
        self.request.session.update(default)
        print('INSTANTIATING FINISHED')

    def set_session_value(self, state, key, value):
        print("SETTING VALUE:", state, key, value)
        if self.is_default_type(state, key, value):
            print('self.is_default_type', state, key, value)
            old_value = self.request.session[state].get(key)
            if old_value != value:
                self.request.session[state][key] = value
                self.request.session.modified = True
                print('\nupdated {} with old value {} with new value {'
                      '}'.format(
                    key, old_value, value))
                # pprint(dict(self.request.session))
        else:
            print('NOT MY TYPE!:', state, key, value)
            print('default:', type(DEFAULT_STATE[state][key]).__name__)
            print('new:', type(value).__name__)

    def is_default_type(self, state, key, value):
        try:
            return isinstance(value, type(DEFAULT_STATE[state][key]))
        except KeyError:
            return True

    def undo(self):
        remove = self.tab_order[self.last - 1]
        self.request.session['redo'][remove] = self.request.session[remove]
        if remove != 'startpage':
            self.disabled_state[remove] = 'disabled'
        self.request.session[remove] = {}
        self.request.session.modified = True

    def redo(self):
        redo = self.tab_order[self.last]
        new_redo = self.request.session['redo'][redo]
        if new_redo:
            self.request.session['disabled'][redo] = ''
            self.request.session[redo] = new_redo
            self.request.session.modified = True

    @cached_property
    def last(self):
        self.request.session['redo'] = self.request.session.get(
            'redo',
            {key: self.request.session.get(key, value) for key, value in
             DEFAULT_STATE.items()}
        )
        for i, status in enumerate(self.tab_order):
            if self.request.session['disabled'][status] == 'disabled':
                break
        return i

    # ------------------------------------------------------------------------ #
    ### Page properties
    @cached_property
    def menu(self):
        return [
            (i + 1, title, description, link,
             self.request.session['disabled'][link] if link != self.active else 'active')
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
        return self.request.session['startpage'].get(
            'measurement_point', 'No Time Series Selected')

    # ------------------------------------------------------------------------ #
    ### Map properties
    @cached_property
    def selected_coords(self):
        return json.dumps([float(x) for x in self.request.session['startpage'].get(
            'selected_coords', [])])

    @property
    def center(self):
        try:
            return [float(x) for x in self.request.session['map_'].get('center',
                                                                       [45, 0])]
        except KeyError:
            return [45.0, 0.0]

    @property
    def zoom(self):
        try:
            return self.request.session['map_'].get('zoom', 3)
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

    # ------------------------------------------------------------------------ #
    ### Data handling

    @cached_property
    def timeseries(self):
        ts = GroundwaterTimeSeries()
        ts.uuid(self.request.session['startpage']['uuid'], **self.time_window)
        if len(ts.results) != 0:
            data = [{'y': x['max'], 'x': x['timestamp']}
                             for x in ts.results[0]['events']]
        else:
            data = []

        self.data = {
            'values': data,
            'key': 'Groundwaterlevels (m)',
            'color': '#1abc9c'
        }

        return self.data

    @cached_property
    def error_message(self):
        if len(self.timeseries['values']) == 0:
            return 'No time series found for this location, please select ' \
                   'another.'
        return ''

    # ------------------------------------------------------------------------ #
    ### Date handling
    JS_EPOCH = dt.datetime(1970, 1, 1)

    def datetime_to_js(self, date_time):
        if date_time is not None:
            return int((date_time - self.JS_EPOCH).total_seconds() * 1000)

    def js_to_datetime(self, date_time):
        if date_time is not None:
            return self.JS_EPOCH + dt.timedelta(seconds=date_time/1000)

    @cached_property
    def today(self):
        return today()

    # @cached_property
    # def current(self):
    #     return self.active if self.active else 'map_'
    #
    # @cached_property
    # def start(self):
    #     start_old = self.request.session[self.current].get('start', self.today)
    #     return self.request.GET.get('start', start_old)
    #
    # @cached_property
    # def end(self):
    #     start_old = self.request.session[self.current].get('end', self.today)
    #     return self.request.GET.get('end', start_old)

    @property
    def time_window(self):
        start = self.datetime_to_js(dt.datetime.strptime(
            self.request.session['startpage']['datepicker']['start'], '%d-%m-%Y'
        ))
        end = self.datetime_to_js(dt.datetime.strptime(
            self.request.session['startpage']['datepicker']['end'], '%d-%m-%Y'
        ))
        return {
            'start': start,
            'end': end
        }

    # ------------------------------------------------------------------------ #
    ### Button handling:

    @cached_property
    def spinner_value(self):
        return self.request.session[self.active]['spinner']['value']

    @cached_property
    def dropdown_selected(self):
        return self.request.session[self.active]['dropdown']['value']

    @cached_property
    def dropdown_unselected(self):
        return [x for x in self.dropdown_options if x != self.dropdown_selected]

    @cached_property
    def datepicker_start(self):
        return [int(x) for x in self.request.session['startpage']['datepicker']['start'].split('-')]

    @cached_property
    def datepicker_end(self):
        return [int(x) for x in self.request.session['startpage']['datepicker']['end'].split('-')]


class FreqTemplateView(TemplateView):

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
    # statistic_options = ('min', 'max', 'mean')
    #
    # @property
    # def active_statistic(self):
    #     return self.request.session['map_'].get('active_statistic', 'mean')
    #
    # @property
    # def statistics(self):
    #     return [s for s in self.statistic_options if s != self.active_statistic]
    # TODO: update to spinners and other buttons


class StartPageBaseView(BaseView):
    active = 'startpage'
    freq_active = 'active'
    template_name = 'freq/startpage.html'


class StartPageView(StartPageBaseView):
    active = 'startpage'
    freq_active = 'active'
    template_name = 'freq/startpage.html'

    def dispatch(self, *args, **kwargs):  # TODO: PUT IN ALL VIEWS
        if not self.request.session.get('session_is_set', False):
            self.instantiate_session()
        return super().dispatch(*args, **kwargs)


class ReStartPageView(StartPageView):

    def get(self, request, *args, **kwargs):
        self.instantiate_session()
        return super().get(request, *args, **kwargs)


class TimeSeriesByLocationUUIDView(StartPageBaseView):
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
            self.set_session_value('startpage', 'measurement_point',
                "Meetpunt: " + result['name'])
            self.request.session['disabled']['trend_detection'] = ''
            self.request.session.modified = True
            self.set_session_value('trend_detection', 'active', True)
            self.set_session_value('startpage', 'start_js', result['first_value_timestamp'])
            self.set_session_value('startpage', 'end_js', result['last_value_timestamp'])
            self.set_session_value('startpage', 'uuid', result['uuid'])
        return []

    @cached_property
    def uuid(self):
        return self.request.GET['uuid']

    @cached_property
    def coordinates(self):
        return [self.request.GET['x_coord'], self.request.GET['y_coord']]

    def get(self, request, *args, **kwargs):
        self.request.session['startpage']['selected_coords'] = self.coordinates
        self.request.session['map_']['center'] = self.coordinates
        self.request.session.modified = True
        return super().get(request, *args, **kwargs)


class TimeSeriesByUUIDView(StartPageBaseView):

    def to_date(self, date_extreme):
        return self.js_to_datetime(int(self.request.GET[date_extreme])
                                   ).strftime('%d-%m-%Y')

    @property
    def startdate(self):
        return self.to_date('start')

    @property
    def enddate(self):
        return self.to_date('end')

    def get(self, request, uuid, *args, **kwargs):
        print('oughta be setting a lot of session values right now:')
        self.set_session_value('startpage', 'measurement_point',
                               "Meetpunt: " + self.request.GET['name'])
        self.set_session_value('startpage', 'datepicker',
                               {
                                    'start': self.startdate,
                                    'end': self.enddate
                               })
        self.set_session_value('startpage', 'start_js', request.GET['start'])
        self.set_session_value('startpage', 'end_js', request.GET['end'])
        self.set_session_value('startpage', 'uuid', uuid)
        self.request.session['disabled']['trend_detection'] = 'enabled'
        self.request.session.modified = True
        self.set_session_value('trend_detection', 'active', True)
        self.chart = ''
        print('Finished setting a lot of session values')
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
    dropdown_options = [
        "Linear trend",
        "Step trend"
    ]


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
        return self.request.session['periodic_fluctuations'].get(
            'spinner', {'value': '0'})['value']


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


class BaseApiView(BaseViewMixin, APIView):

    def get(self, request, *args, **kwargs):
        if self.button == 'datepicker':
            self.set_session_value(
                'startpage', self.button,
                json.loads(self.request.GET.get('value', self.request.session[
                    'startpage']['datepicker']))
            )
        elif self.button:
            self.set_session_value(self.active, self.button, self.value)
        print('BASE RESPONSE', self.base_response)
        return RestResponse(self.base_response)

    def pd_timeseries_from_json(self, json_data, name=''):
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
    def value(self):  #TODO: remove errors
        value = self.request.GET.get('value')
        if value is None:
            print("ERROR BUTTON VALUE == NONE!: ",
                  self.button, value)
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            print("ERROR BUTTON VALUE IS NOT A JSON: ", self.button, value)
            return value

    @property
    def pd_timeseries(self):
        return self.pd_timeseries_from_json(self.timeseries)

    @property
    def base_response(self):
        response = {
            'name': 'chart',
            'data': self.timeseries
        }
        response.update(self.additional_response)
        return [response]

    @property
    def additional_response(self):
        return {}


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
        self.set_session_value(
            'map_',
            'center',
            [
                mean([coordinates['SWlat'], coordinates['NElat']]),
                mean([coordinates['SWlng'], coordinates['NElng']])
            ]
        )
        return [coordinates['SWlng'], coordinates['SWlat'],
                coordinates['NElng'], coordinates['NElat']]


class TimeSeriesDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        response_dict = {
            'data': self.timeseries,
            'start': self.request.session['startpage']['start_js'],
            'end': self.request.session['startpage']['end_js'],
            'uuid': self.request.session['startpage']['uuid'],
            'name': self.request.session['startpage']['measurement_point']
        }
        return RestResponse(response_dict)


class StartpageDataView(BaseApiView):
    active = 'startpage'

    @property
    def additional_response(self):
        return {}


class TrendDataView(BaseApiView):
    active = 'trend_detection'

    @property
    def additional_response(self):
        return {}


class FluctuationsDataView(BaseApiView):
    active = 'periodic_fluctuations'

    @property
    def additional_response(self):
        return {}


class RegressiveDataView(BaseApiView):
    active = 'autoregressive'

    @property
    def additional_response(self):
        return {}


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
