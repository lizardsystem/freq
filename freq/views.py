# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
import copy
import datetime as dt
import json
from pprint import pprint  # left here for debugging purposes
from statistics import mean

from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView

import numpy as np
import pandas as pd
from rest_framework.response import Response as RestResponse
from rest_framework.views import APIView

import freq.jsdatetime as jsdt
from freq.buttons import *
import freq.freq_calculator as calculator
from freq.lizard_api import ApiError
from freq.lizard_api import GroundwaterLocations
from freq.lizard_api import GroundwaterTimeSeries


TIMESERIES_MEASUREMENT_FREQUENCY = 'M'
DEFAULT_STATE = {
    'map_': {
        'bounds': [
            [48.0, -6.8],
            [56.2, 18.9]
        ],
        'datepicker': {'start': '1-1-1900', 'end': jsdt.today()},
        'dropdown_0': {'value': 'mean'},
    },
    'startpage': {
        'chart': 'hidden',
        'datepicker': {'start': '1-1-1900', 'end': jsdt.today()},
        'end_js': 1000000000000,
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'measurement_point': 'No Time Series Selected',
        'selected_coords': [],
        'start_js': 0,
        'timeseries_length': -9999,
        'uuid': 'EMPTY',
    },
    'trend_detection': {
        'active': False,
        'datepicker': {'start': '1-1-1900', 'end': jsdt.today()},
        'dropdown_0': {'value': '... (choose type)'},
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'spinner_0': {'value': 0.05},
    },
    'periodic_fluctuations': {
        'spinner_0': {'value': 10},
        'spinner_1': {'value': 0},
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'autoregressive': {
        'spinner_0': {'value': 1},
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
    spinners = []

    # ------------------------------------------------------------------------ #
    ### Session handling

    ## Use for debugging:
    # def dispatch(self, *args, **kwargs):
    #     print('\n\n\nIN {}'.format(type(self).__name__))
    #     pprint(dict(self.request.session))
    #     return super().dispatch(*args, **kwargs)

    def instantiate_session(self):
        self.request.session['session_is_set'] = True
        default = copy.deepcopy(DEFAULT_STATE)
        self.request.session.update(default)

    def set_session_value(self, state, key, value):
        if self.is_default_type(state, key, value):
            old_value = self.request.session[state].get(key)
            if old_value != value:
                self.request.session[state][key] = value
                self.request.session.modified = True
                print('\nupdated {} with old value {} with new value {'
                      '}'.format(
                    key, old_value, value))
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
            self.request.session['disabled'][remove] = 'disabled'
        default = copy.deepcopy(DEFAULT_STATE)
        self.request.session[remove] = default[remove]
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
        return [float(x) for x in self.request.session['map_'].get('center',
                                                                       [45, 0])]

    @property
    def bounds(self):
        return self.request.session['map_'].get('bounds')

    @property
    def zoom(self):
        if self.request.session['startpage']['selected_coords']:
            return 10
        return self.request.session['map_'].get('zoom', 3)

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

        self.request.session['startpage']['timeseries_length'] = len(data)
        self.request.session.modified = True

        return self.data


    @cached_property
    def error_message(self):
        if len(self.timeseries['values']) == 0:
            return 'No time series found for this location, please select ' \
                   'another.'
        return ''

    # ------------------------------------------------------------------------ #
    ### Date handling

    @cached_property
    def today(self):
        return jsdt.today()

    @property
    def time_window(self):
        start = jsdt.datetime_to_js(dt.datetime.strptime(
            self.request.session['startpage']['datepicker']['start'], '%d-%m-%Y'
        ))
        end = jsdt.datetime_to_js(dt.datetime.strptime(
            self.request.session['startpage']['datepicker']['end'], '%d-%m-%Y'
        ))
        return {
            'start': start,
            'end': end
        }

    # ------------------------------------------------------------------------ #
    ### Button handling:

    @cached_property
    def length(self):
        length = self.request.session['startpage']['timeseries_length']
        if length < 0:
            return len(self.timeseries['values'])
        return length

    @cached_property
    def spinner_value(self):
        return self.request.session[self.active]['spinner_0']['value']

    @cached_property
    def dropdown_selected(self):
        return self.request.session[self.active]['dropdown_0']['value']

    @cached_property
    def dropdown_unselected(self):
        return [x for x in self.dropdown_options if x != self.dropdown_selected]

    @cached_property
    def datepicker_start(self):
        start = self.request.session['startpage']['datepicker']['start']
        if isinstance(start, str) and '-' in start:
            return [int(x) for x in start.split('-')]
        else:
            raise TypeError('datepicker start is invalid')

    @cached_property
    def datepicker_end(self):
        end = self.request.session['startpage']['datepicker']['end']
        if isinstance(end, str) and '-' in end:
            return [int(x) for x in end.split('-')]
        else:
            raise TypeError('datepicker end is invalid')


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
    dropdowns = DropDown(
        heading= "Statistic",
    )
    dropdown_options= [
        "min",
        "max",
        "mean"
    ]

    def dispatch(self, *args, **kwargs):
        if not self.request.session.get('session_is_set', False):
            self.instantiate_session()
        return super().dispatch(*args, **kwargs)


class StartPageBaseView(BaseView):
    active = 'startpage'
    freq_active = 'active'
    template_name = 'freq/startpage.html'


class StartPageView(StartPageBaseView):
    active = 'startpage'
    freq_active = 'active'
    template_name = 'freq/startpage.html'

    def dispatch(self, *args, **kwargs):
        if not self.request.session.get('session_is_set', False):
            self.instantiate_session()
        return super().dispatch(*args, **kwargs)


class ReStartPageView(StartPageView):

    def dispatch(self, *args, **kwargs):
        self.instantiate_session()
        return super().dispatch(*args, **kwargs)


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
            self.set_session_value('disabled', 'trend_detection', 'enabled')
            self.request.session.modified = True
            self.set_session_value('trend_detection', 'active', True)
            self.set_session_value('periodic_fluctuations', 'active', True)
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

    @cached_property
    def bounds(self):
        x = float(self.request.GET['x_coord'])
        y = float(self.request.GET['y_coord'])
        bounds = [[y - 0.25, x -0.25], [y + 0.25, x + 0.25]]
        return bounds

    def get(self, request, *args, **kwargs):
        self.request.session['startpage']['selected_coords'] = self.coordinates
        self.request.session['map_']['bounds'] = self.bounds
        self.request.session.modified = True
        return super().get(request, *args, **kwargs)


class TimeSeriesByUUIDView(StartPageBaseView):

    def to_date(self, date_extreme):
        return jsdt.js_to_datetime(int(self.request.GET[date_extreme])
                                   ).strftime('%d-%m-%Y')

    @property
    def startdate(self):
        return self.to_date('start')

    @property
    def enddate(self):
        return self.to_date('end')

    def get(self, request, uuid, *args, **kwargs):
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
        return super().get(request, *args, **kwargs)


class TrendDetectionView(BaseView):
    freq_active = 'active'
    active = 'trend_detection'
    template_name = 'freq/trend_detection.html'
    spinners = Spinner(
        heading='Alpha (significance)',
        title="alpha (significance of the t-test for changes in the " \
                    "mean (0-1))",
        min_=0.01,
        step=0.01,
        precision=2
    )

    dropdowns = DropDown(
        heading= "Trend type",
    )
    spinner_max = 0.99
    dropdown_options= [
        "Both trends",
        "Linear trend",
        "Step trend"
    ]


class PeriodicFluctuationsView(BaseView):
    freq_active = 'active'
    active = 'periodic_fluctuations'
    template_name = 'freq/periodic_fluctuations.html'
    spinners = [
        Spinner(
            heading='Correlation lags',
            title="Number of lags used for the correlogram computation",
            number=0
        ),
        Spinner(
            heading='Number of harmonics',
            title="Number of harmonics to be removed from the series",
            number=1
        )
    ]

    @property
    def spinner_max(self):
        return int(self.length / 2)

    @property
    def spinner_1_value(self):
        return self.request.session['periodic_fluctuations'].get(
            'spinner_1', {'value': '0'})['value']


class AutoRegressiveView(BaseView):
    freq_active = 'active'
    active = 'autoregressive'
    template_name = 'freq/autoregressive.html'
    spinners = Spinner(
        heading='Number of periods',
        title="Number of periods used in the training of the autoregressive " \
               "model",
        min_=1
    )

    @property
    def spinner_max(self):
        return int(0.3 * self.length)


class BaseApiView(BaseViewMixin, APIView):
    text_output = []

    def get(self, request, *args, **kwargs):
        if self.button == 'datepicker':
            self.set_session_value(
                'startpage', self.button,
                json.loads(self.request.GET.get('value', self.request.session[
                    'startpage']['datepicker']))
            )
        elif self.button and self.button != 'undefined':
            next_tab = {
                'trend_detection': 'periodic_fluctuations',
                'periodic_fluctuations': 'autoregressive'
            }.get(self.active, False)
            if next_tab:
                self.set_session_value('disabled', next_tab, 'enabled')
            self.set_session_value(self.active, self.button, self.value)
        return RestResponse(self.base_response)

    def pd_timeseries_from_json(self, json_data, name=''):
        # store results in a numpy array
        dates = np.array([jsdt.js_to_datestring(x['x']) for x in json_data],
                         dtype='datetime64')
        values = np.array([y['y'] for y in json_data])
        index = pd.DatetimeIndex(dates, freq='infer')
        # build a timeseries object so we can compare it with other timeseries
        timeseries = pd.Series(values, index=index, name=name)
        return timeseries

    def load_timeseries(self, timeseries_values, name):
        timeseries_raw = self.pd_timeseries_from_json(timeseries_values, name)
        return calculator.load(
            data=timeseries_raw,
            data_path=None,
            init_date=None,
            end_date=None,
            frequency=TIMESERIES_MEASUREMENT_FREQUENCY,
            interpolation_method='linear',
            delimiter=';'
        )

    def series_to_js(self, npseries, index, key, color='#2980b9', dates=True):
        values = [{'x': jsdt.datetime_to_js(index[i]) if dates else i,
                   'y': float(value)}
                for i, value in enumerate(npseries)]
        return {
            'values': values,
            'key': key,
            'color': color
        }

    def linear_trend(self, timeseries=None, name=None):
        if timeseries is None:
            timeseries = self.timeseries['values']
            if not name:
                name = self.timeseries['key']
            timeseries = self.load_timeseries(timeseries, name)[1]
        result = calculator.linear(
            data=timeseries,
            alpha=float(self.request.session[
                                'trend_detection']['spinner_0']['value']),
            detrend_anyway=True
        )
        return [result]

    def step_trend(self):
        timeseries = self.load_timeseries(self.timeseries['values'],
                                          self.timeseries['key'])
        try:
            split = int(self.request.session['trend_detection']['graph']['x'])
            if split == 0:
                return
            breakpoint = jsdt.js_to_datetime(split)
            return [calculator.step(
                data=timeseries[1],
                bp=int(timeseries[0].index.searchsorted(breakpoint)),
                alpha=float(self.request.session[
                                'trend_detection']['spinner_0']['value']),
                detrend_anyway=True
            )]
        except KeyError:
            return

    def both_trends(self):
        try:
            step = self.step_trend()[0]
            return [step, self.linear_trend(step[0])[0]]
        except TypeError:
            return

    @cached_property
    def pandas_timeseries(self):
        return self.load_timeseries(self.timeseries['values'],
                                          self.timeseries['key'])

    @cached_property
    def selected_trend(self):
        selected_trend_type = self.request.session['trend_detection'][
            'dropdown_0']['value']
        if '...' in selected_trend_type:
            return
        self.set_session_value('disabled', 'periodic_fluctuations', 'enabled')
        self.set_session_value('periodic_fluctuations', 'active', True)
        if 'Linear' in selected_trend_type:
            return self.linear_trend()
        elif 'Step' in selected_trend_type:
            return self.step_trend()
        elif 'Both' in selected_trend_type:
            return self.both_trends()
        raise ValueError('Trend type unknown: ' + str(selected_trend_type))

    @cached_property
    def correllogram(self):
        return calculator.correlogram(
            data=self.selected_trend[-1][0],
            n_lags=int(self.request.session['periodic_fluctuations'][
                'spinner_0']['value'])
        )

    @cached_property
    def harmonic(self):
        return calculator.harmonic(
            data=self.selected_trend[-1][0],
            n_harmonics=int(self.request.session['periodic_fluctuations'][
                'spinner_1']['value'])
        )

    @cached_property
    def autoregressive(self):
        return calculator.autoregressive(
            data=self.harmonic[0],
            per=int(self.request.session['autoregressive'][
                'spinner_0']['value'])
        )

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

    @cached_property
    def additional_response(self):
        """Overwrite this property"""
        return [[self.timeseries]]

    @property
    def base_response(self):
        response = []
        for i in range(len(self.additional_response)):
            response.append({
                'name': '#chart_' + str(i) + ' svg',
                'data': self.additional_response[i]
            })

        return {
            'graphs': response,
            'statistics': self.text_output
        }

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


class MapDataView(BaseApiView):
    active = 'map_'

    def get(self, request, *args, **kwargs):
        super().get(self, request, *args, **kwargs)
        datatypes = request.GET.get('datatypes', 'locations,timeseries').split(
            ',')
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
        return locations.coord_uuid_name()

    @property
    def timeseries(self):
        extreme = self.request.session['map_'].get(
            'dropdown_0', {'value': 'mean'})['value']
        timeseries = GroundwaterTimeSeries()
        timeseries.queries = {
            "name": self.request.GET.get("groundwater_type", "GWmMSL")
        }
        timeseries.from_bbox(*self.coordinates, **self.time_window)
        return timeseries.min_max_mean(
            extreme=extreme,
            start_date=self.request.session['map_']['datepicker']['start'],
            end_date=self.request.session['map_']['datepicker']['end']
        )

    @cached_property
    def coordinates(self):
        try:
            bounds = json.loads(self.request.GET.get('bounds'))
            bounds_array = [
                [bounds['_southWest']['lat'], bounds['_southWest']['lng']],
                [bounds['_northEast']['lat'], bounds['_northEast']['lng']]
            ]
            self.set_session_value('map_', 'bounds', bounds_array)
        except TypeError:
            bounds_array = self.request.session['map_'].get('bounds')
        return bounds_array

    @property
    def base_response(self):
        return {}


class StartpageDataView(BaseApiView):
    active = 'startpage'


class TrendDataView(BaseApiView):
    active = 'trend_detection'

    @cached_property
    def additional_response(self):
        result = []
        if self.selected_trend is None:
            return [[self.timeseries]]
        result.append([
            self.timeseries,
            self.series_to_js(
                npseries=self.selected_trend[0][0],
                index=self.pandas_timeseries[0].index,
                key='Detrended groundwaterlevels (m)'
            ),
            self.series_to_js(
                npseries=self.selected_trend[0][1],
                index=self.pandas_timeseries[0].index,
                key='Removed trend (m)',
                color='#f39c12'
            ),
        ])
        self.text_output = [self.selected_trend[0][3]]
        try:
            result.append([
                self.series_to_js(
                    npseries=self.selected_trend[0][0],
                    index=self.pandas_timeseries[0].index,
                    key='Detrended groundwaterlevels [step trend] (m)',
                    color='#1abc9c'
                ),
                self.series_to_js(
                    npseries=self.selected_trend[1][0],
                    index=self.pandas_timeseries[0].index,
                    key='Detrended groundwaterlevels [linear trend] (m)'
                ),
                self.series_to_js(
                    npseries=self.selected_trend[1][1],
                    index=self.pandas_timeseries[0].index,
                    key='Removed trend (m)',
                    color='#f39c12'
                ),
            ])
            self.text_output.append(self.selected_trend[0][3])
        except IndexError:
            pass
        return result


class FluctuationsDataView(BaseApiView):
    active = 'periodic_fluctuations'

    @cached_property
    def additional_response(self):
        return [[
            self.series_to_js(
                npseries=self.correllogram,
                index=[],
                key='Cumulative Periodogram (Cp)',
                dates=False
            )
        ], [
            self.series_to_js(
                npseries=self.selected_trend[-1][0],
                index=self.pandas_timeseries[0].index,
                key='Detrended groundwaterlevels (m)',
                color='#1abc9c'
            ),
            self.series_to_js(
                npseries=self.harmonic[0],
                index=self.pandas_timeseries[0].index,
                key='Groundwaterlevels with periodic fluctuations removed (m)'
            ),
            self.series_to_js(
                npseries=self.harmonic[1],
                index=self.pandas_timeseries[0].index,
                key='Removed periodic fluctuations (m)',
                color='#f39c12'
            ),
        ]]


class RegressiveDataView(BaseApiView):
    active = 'autoregressive'

    @cached_property
    def additional_response(self):
        return [[
            self.series_to_js(
                npseries=self.harmonic[0],
                index=self.pandas_timeseries[0].index,
                key='Groundwaterlevels with periodic fluctuations removed (m)',
                color='#1abc9c'
            ),
            self.series_to_js(
                npseries=self.autoregressive[0],
                index=self.pandas_timeseries[0].index,
                key='Autoregressive model result (m)'
            ),
            self.series_to_js(
                npseries=self.autoregressive[1],
                index=self.pandas_timeseries[0].index,
                key='Removed trend',
                color='#f39c12'
            ),
        ]]