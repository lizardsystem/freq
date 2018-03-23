# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
import copy
import csv
import datetime
import json
import logging
import re

from django.utils.functional import cached_property
from django.utils.text import slugify
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.conf import settings

import numpy as np
import pandas as pd
from rest_framework.response import Response as RestResponse
from rest_framework.views import APIView
from lizard_auth_client.models import Organisation

import freq.jsdatetime as jsdt
from freq.buttons import *
import freq.freq_calculator as calculator
from freq.lizard_connector import Filters
from freq.lizard_connector import GroundwaterLocations
from freq.lizard_connector import GroundwaterTimeSeries
from freq.lizard_connector import LizardApiError
from freq.lizard_connector import RasterFeatureInfo
from freq.lizard_connector import RasterLimits
from freq.lizard_connector import Users

logger = logging.getLogger(__name__)


TIMESERIES_MEASUREMENT_FREQUENCY = 'M'
DEFAULT_STATE = {
    'login': {
        'selected_organisation': '',
        'selected_organisation_id': '',
    },
    'map_': {
        'bounds': [
            [15, 90],
            [5, 110]
        ],
        'datepicker': {'start': '1-1-1930', 'end': jsdt.today()},
        'dropdown_0': {'value': 'GWmBGS | mean'},
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'measurement_point': 'No Time Series Selected',
        'uuid': 'EMPTY',
        'end_js': 1000000000000,
        'timeseries_length': -9999,
        'start_js': -1262304000000,
    },
    'startpage': {
        'datepicker': {'start': '1-1-1930', 'end': jsdt.today()},
        'end_js': 1000000000000,
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'measurement_point': 'No Time Series Selected',
        'selected_coords': [],
        'start_js': -1262304000000,
        'timeseries_length': -9999,
        'uuid': 'EMPTY',
        'timeseries_selection': ()
    },
    'trend_detection': {
        'active': False,
        'datepicker': {'start': '1-1-1900', 'end': jsdt.today()},
        'dropdown_0': {'value': '... (choose type)'},
        'graph': {'x': 0, 'y': 0, 'series': 0},
        'spinner_0': {'value': 0.05},
    },
    'periodic_fluctuations': {
        'spinner_0': {'value': 0},
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'autoregressive': {
        'spinner_0': {'value': 10},
        'spinner_1': {'value': 1},
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'additive': {
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'frequency': {
        'graph': {'x': 0, 'y': 0, 'series': 0},
    },
    'disabled': {
        'startpage': 'enabled',
        'trend_detection': 'disabled',
        'periodic_fluctuations': 'disabled',
        'autoregressive': 'disabled',
        'additive': 'disabled',
        'frequency': 'disabled'
    },
}

ks = [k for k in DEFAULT_STATE.keys()]  # for debugging


class BaseViewMixin(object):
    """Base view."""
    template_name = 'freq/base.html'
    title = 'GGMN - Global Groundwater Network'
    page_title = 'GGMN - Global Groundwater Network'
    menu_items = [
        ('Startpage', 'Back to Homepage', 'startpage'),
        ('Detection of Trends', 'Step trend or flat trend detection',
            'trend_detection'),
        ('Periodic Fluctuations', 'Estimate periodic fluctuations by harmonic '
            'analysis', 'periodic_fluctuations'),
        ('Autoregressive Model', 'Analyse the resulting, now stationary, time '
            'series with an autoregressive model (ARM)', 'autoregressive'),
        ('Additive Model', 'Analysis of model results',
            'additive'),
        ('Sampling Frequency', 'Analysis and design of sampling frequency',
            'frequency'),
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
        self.request.session.modified = True

    def set_session_value(self, state, key, value):
        if self.is_default_type(state, key, value):
            old_value = self.request.session[state].get(key)
            skip = True
            if old_value != value:
                skip = False
                if isinstance(value, dict):
                    if any(not v for k, v in value.items() if not k ==
                            'series'):
                       skip = True
            if not skip:
                self.request.session[state][key] = value
                self.request.session.modified = True
                # logger.debug('updated {} with old value {} with new '
                #                  'value {'
                #       '}'.format(
                #     key, old_value, value))
        else:
            # logger.warn('NOT MY TYPE!: {}, {}, {}'.format(state, key, value))
            # logger.warn('default: {}'.format(
            #     type(DEFAULT_STATE[state][key]).__name__))
            # logger.warn('new: {}'.format(type(value).__name__))
            pass

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
    def no_debug(self):
        return not settings.DEBUG

    @cached_property
    def menu(self):
        return [
            (i + 1, title, description, link,
             self.request.session['disabled'][link] if link != self.active else 'active')
            for i, (title, description, link) in enumerate(self.menu_items)
        ]

    @cached_property
    def error_message(self):
        return self.request.GET.get('error_message', '')

    @cached_property
    def show_error(self):
        if not self.error_message:
            return 'hidden'
        return ''

    @cached_property
    def measurement_point(self):
        page = self.request.GET.get('active', 'startpage')
        return self.request.session[page].get(
            'measurement_point', 'No Time Series Selected')

    # ------------------------------------------------------------------------ #
    ### Map properties
    @cached_property
    def selected_coords(self):
        page = self.request.GET.get('active', 'startpage')
        return json.dumps([float(x) for x in self.request.session[page].get(
            'selected_coords', [])])

    @property
    def center(self):
        return [float(x) for x in self.request.session['map_'].get('center',
                                                                       [45, 0])]

    @property
    def bounds(self):
        return self.request.session['map_'].get('bounds')

    @property
    def freq_icon_size(self):
        if self.active == 'map_' or self.active == 'lizard':
            return "glyphicon-sm"
        else:
            return ""

    @property
    def map_icon_size(self):
        if self.active != 'map_':
            return "glyphicon-sm"
        else:
            return ""

    @property
    def lizard_icon_size(self):
        if self.active != 'lizard':
            return "glyphicon-sm"
        return ""

    # ------------------------------------------------------------------------ #
    ### Data handling

    @cached_property
    def timeseries(self):
        ts = GroundwaterTimeSeries(use_header=self.logged_in)
        page = self.request.GET.get('active', 'startpage')
        uuid = self.request.session[page]['uuid']
        data = []
        if uuid != "EMPTY":
            ts.uuid(ts_uuid=self.request.session[page]['uuid'],
                    organisation=self.selected_organisation_id, **self.time_window)
            if len(ts.results):
                data = [{'y': x['max'], 'x': x['timestamp']}
                                 for x in ts.results[0]['events']]

        self.data = {
            'values': data,
            'key': 'Groundwaterlevels (m)',
            'color': '#1abc9c'
        }

        self.request.session[page]['timeseries_length'] = len(data)
        self.request.session.modified = True

        return self.data


    @cached_property
    def error_message(self):
        if not len(self.timeseries['values']):
            return 'Please select a location.'
        return ''

    # ------------------------------------------------------------------------ #
    ### Date handling

    @cached_property
    def today(self):
        return jsdt.today()

    @property
    def datepicker_page(self):
        return "map_" if self.active == "map_" else "startpage"

    @property
    def time_window(self):
        page = self.datepicker_page
        start = jsdt.datetime_to_js(datetime.datetime.strptime(
            self.request.session[page]['datepicker']['start'], '%d-%m-%Y'
        ))
        end = jsdt.datetime_to_js(datetime.datetime.strptime(
            self.request.session[page]['datepicker']['end'], '%d-%m-%Y'
        ))
        return {
            'start': start,
            'end': end
        }

    # ------------------------------------------------------------------------ #
    ### Button handling:

    @cached_property
    def length(self):
        page = self.request.GET.get('active', 'startpage')
        length = self.request.session[page]['timeseries_length']
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
        page = self.datepicker_page
        start = self.request.session[page]['datepicker']['start']
        if isinstance(start, str) and '-' in start:
            return [int(x) for x in start.split('-')]
        else:
            raise TypeError('datepicker start is invalid')

    @cached_property
    def datepicker_end(self):
        page = self.datepicker_page
        end = self.request.session[page]['datepicker']['end']
        if isinstance(end, str) and '-' in end:
            return [int(x) for x in end.split('-')]
        else:
            raise TypeError('datepicker end is invalid')

    @cached_property
    def nav_dropdown(self):
        return DropDown(
            heading="Organisation",
            title="Choose ",
            id_=999
        )

    # ------------------------------------------------------------------------ #
    ### Login related:
    @cached_property
    def organisations_id_name(self):
        if self.logged_in:
            users = Users(use_header=True)
            return users.get_organisations(username=self.user)
        else:
            return []

    @cached_property
    def organisations_id(self):
        return [x[1] for x in self.organisations_id_name]

    @cached_property
    def organisations(self):
        return [x[0] for x in self.organisations_id_name]

    def _selected_organisation(self, organisations, ext=''):
        if self.logged_in:
            default_login = copy.deepcopy(DEFAULT_STATE['login'])
            org = self.request.session.get('login', default_login)[
                'selected_organisation' + ext]
            if org:
                return org
            try:
                org = organisations[0]
                return org
            except IndexError:
                return

    @cached_property
    def selected_organisation(self):
        return self._selected_organisation(self.organisations)

    @cached_property
    def selected_organisation_id(self):
        return self._selected_organisation(self.organisations_id, '_id')

    @cached_property
    def logged_in(self):
        return self.request.user.is_authenticated()

    @cached_property
    def user(self):
        return self.request.user

    @cached_property
    def reference(self):
        if self.active == 'map_':
            ref_value = self.request.session['map_']['dropdown_0']['value']
        else:
            ref_value = self.request.session['startpage']['measurement_point']
        if 'BGS' in ref_value:
            return 'BGS'
        if 'MSL' in ref_value:
            return 'MSL'
        return ''


class FreqTemplateView(TemplateView):

    def get(self, request, *args, **kwargs):
        if request.GET.get('undo', False):
            self.undo()
        elif request.GET.get('redo', False):
            self.redo()
        return super().get(request, *args, **kwargs)


class BaseView(BaseViewMixin, FreqTemplateView):

    @property
    def timeseries_selection(self):
        return self.request.session['startpage']['timeseries_selection']


class GlobalView(BaseView):
    active = 'lizard'
    lizard_active = 'active'
    template_name = 'freq/lizard_iframe.html'
    menu_items = []

    def dispatch(self, *args, **kwargs):
        if not self.request.session.get('session_is_set', False):
            self.instantiate_session()
        return super().dispatch(*args, **kwargs)

    @property
    def iframe_url(self):
        today = datetime.datetime.today().strftime("%b,%d,%Y")
        return settings.IFRAME_BASE_URL + "en/map/topography,gwaterchain,dataavailability/point@27.7613,-38.1445,3/Jan,01,1940-{today}".format(today=today)


class RegionalMapView(BaseView):
    active = 'map_'
    template_name = 'freq/map.html'
    menu_items = []
    map_active = 'active'
    dropdowns = DropDown(
        heading="Statistic",
        options=[
            "GWmBGS | min",
            "GWmBGS | max",
            "GWmBGS | mean",
            "GWmBGS | range (max - min)",
            "GWmBGS | difference (mean last - first year)",
            "GWmMSL | min",
            "GWmMSL | max",
            "GWmMSL | mean",
            "GWmMSL | range (max - min)",
            "GWmMSL | difference (mean last - first year)"
        ]
    )

    def dispatch(self, *args, **kwargs):
        if not self.request.session.get('session_is_set', False):
            self.instantiate_session()
        return super().dispatch(*args, **kwargs)

    @cached_property
    def interpolation_layers(self):
        return {
            org.name: "extern:igrac:" + org.unique_id for
            org in Organisation.objects.all()
        }


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


class TimeSeriesByLocationUUIDView(StartPageBaseView):
    error_message = ''

    @cached_property
    def timeseries(self):
        ts = GroundwaterTimeSeries(use_header=self.logged_in)
        ts.location_uuid(organisation=self.selected_organisation_id,
                         loc_uuid=self.uuid)
        return ts.results

    @cached_property
    def multiple_timeseries(self):
        return len(self.timeseries) > 0

    @cached_property
    def error_message(self):
        if self.multiple_timeseries:
            return 'Multiple time series found for this location, please ' \
                   'select one below.'
        elif len(self.timeseries) == 0:
            return 'No time series found for this location, please select ' \
                   'another.'
        return ''

    @property
    def timeseries_selection(self):
        _selection = tuple([
            (
                x['location']['name'] + ' - ' + x['name'],
                x['uuid'],
                x['first_value_timestamp'],
                x['last_value_timestamp']
            )
            for x in self.timeseries
        ])
        self.set_session_value('startpage', 'timeseries_selection',
                               _selection)
        return _selection

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
        self.set_session_value(
            'startpage', 'measurement_point', 'No Time Series Selected')
        self.set_session_value('startpage', 'uuid', 'EMPTY')
        self.request.session.modified = True

        page = self.request.GET.get('active', 'startpage')
        self.request.session[page]['selected_coords'] = self.coordinates
        self.request.session['map_']['bounds'] = self.bounds
        if len(self.timeseries) == 1:
            x = self.timeseries[0]
            self.set_session_value('startpage', 'measurement_point',
                                   "Groundwater well: " + x['location']['name']
                                   + ' - ' + x['name'])
            self.set_session_value('startpage', 'datepicker', {
                'start': jsdt.js_to_datetime(
                    int(x['first_value_timestamp'])).strftime('%d-%m-%Y'),
                'end': jsdt.js_to_datetime(
                    int(x['last_value_timestamp'])).strftime('%d-%m-%Y')
            })
            self.set_session_value('startpage', 'start_js', x[
                'first_value_timestamp'])
            self.set_session_value('startpage', 'end_js', x[
                'last_value_timestamp'])
            self.set_session_value('startpage', 'uuid', x['uuid'])
            self.request.session['disabled']['trend_detection'] = 'enabled'
            self.set_session_value('trend_detection', 'active', True)
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
                               "Groundwater well: " + self.request.GET['name'])
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
        heading="Trend type",
        options=[
            "Both trends",
            "Linear trend",
            "Step trend",
            "No trend"
        ]
    )
    spinner_max = 0.99


class PeriodicFluctuationsView(BaseView):
    freq_active = 'active'
    active = 'periodic_fluctuations'
    template_name = 'freq/periodic_fluctuations.html'
    spinners = [
        Spinner(
            heading='Number of harmonics',
            title="Number of harmonics to be removed from the series",
        )
    ]

    @property
    def spinner_max(self):
        return int(self.length / 2)


class AutoRegressiveView(BaseView):
    freq_active = 'active'
    active = 'autoregressive'
    template_name = 'freq/autoregressive.html'
    spinners = [
        Spinner(
            heading='Correlation lags',
            title="Number of lags used for the correlogram computation",
        ),
        Spinner(
            heading='Order of AR model (p)',
            title="Order of Autoregressive model (p) used in the training of the autoregressive " \
                   "model",
            min_=1,
            number=1
        )
    ]

    @property
    def spinner_1_value(self):
        return self.request.session['autoregressive'].get(
            'spinner_1', {'value': '1'})['value']

    @property
    def spinner_max(self):
        return int(0.3 * self.length)


class AdditiveView(BaseView):
    freq_active = 'active'
    active = 'additive'
    template_name = 'freq/additive.html'


class FrequencyView(BaseView):
    freq_active = 'active'
    active = 'frequency'
    template_name = 'freq/frequency.html'


class BaseApiView(BaseViewMixin, APIView):
    statistics = []

    def get(self, request, *args, **kwargs):
        if self.button == 'datepicker':
            page = self.datepicker_page
            self.set_session_value(
                page, 'datepicker',
                json.loads(self.request.GET.get('value', self.request.session[
                    page]['datepicker']))
            )
        elif self.button and self.button != 'undefined':
            next_tabs = {
                'trend_detection': ('periodic_fluctuations', ),
                'periodic_fluctuations': ('autoregressive', ),
                'autoregressive': ('additive', 'frequency')
            }.get(self.active, ())
            for tab in next_tabs:
                self.set_session_value('disabled', tab, 'enabled')
            self.set_session_value(self.active, self.button, self.value)
            self.request.session.modified = True
        try:
            return RestResponse(self.base_response)
        except calculator.CalculatorSampleAmountError:
            return RestResponse({
                'error': 'Too little data points to calculate.'})
        except ValueError:
            return RestResponse({'error': 'Value out of range.'})

    def pd_timeseries_from_json(self, json_data, name=''):
        # store results in a numpy array
        dates = np.array(
            [jsdt.js_to_datestring(x['x'], iso=True) for x in json_data],
            dtype='datetime64'
        )
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
        try:
            values = [
                {'x': jsdt.datetime_to_js(index[i]) if dates else float(
                    index[i]), 'y': float(value)} for i, value in
                enumerate(npseries)
            ]
        except IndexError:
            values = [{'x': i, 'y': float(value)} for i, value in enumerate(
                npseries)]
        return {
            'values': values,
            'key': key,
            'color': color
        }

    def linear_trend(self, timeseries=None, name=None):
        if timeseries is None:
            timeseries = self.pandas_timeseries
        result = calculator.linear(
            data=timeseries,
            alpha=float(
                self.request.session['trend_detection']['spinner_0']['value']),
            detrend_anyway=True
        )
        return [result]

    def step_trend(self):
        try:
            split = int(self.request.session['trend_detection']['graph']['x'])
            if split == 0:
                return
            breakpoint = jsdt.js_to_datetime(split)
            return [calculator.step(
                data=self.pandas_timeseries,
                bp=int(self.pandas_timeseries.index.searchsorted(breakpoint)),
                alpha=float(self.request.session[
                                'trend_detection']['spinner_0']['value']),
                detrend_anyway=True
            )]
        except KeyError:
            return

    def no_trend(self):
        try:
            return [calculator.step(
                data=self.pandas_timeseries,
                bp=0,
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
        ts = self.load_timeseries(self.timeseries['values'],
                                  self.timeseries['key'])
        return ts[0]

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
        elif 'No trend' in selected_trend_type:
            return self.no_trend()
        elif 'Both' in selected_trend_type:
            return self.both_trends()
        raise ValueError('Trend type unknown: ' + str(selected_trend_type))

    @cached_property
    def harmonic(self):
        return calculator.harmonic(
            data=self.selected_trend[-1][0],
            n_harmonics=int(self.request.session['periodic_fluctuations'][
                'spinner_0']['value'])
        )

    @cached_property
    def correllogram(self):
        return calculator.correlogram(
            data=self.selected_trend[-1][0],
            n_lags=int(self.request.session['autoregressive'][
                'spinner_0']['value'])
        )

    @cached_property
    def autoregressive(self):
        return calculator.autoregressive(
            data=self.harmonic[0],
            per=int(self.request.session['autoregressive'][
                'spinner_1']['value'])
        )

    @property
    def button(self):
        return self.request.GET.get('button', '')

    @property
    def value(self):  #TODO: remove errors
        value = self.request.GET.get('value')
        if value is None:
            logger.warn("ERROR BUTTON VALUE == NONE!: {}".format(
                  self.button, value))
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            logger.warn("ERROR BUTTON ({}) VALUE ({}) IS NOT A JSON".format(
                self.button, value))
            return value

    @cached_property
    def additional_response(self):
        """Overwrite this property"""
        return [[self.timeseries]]

    @property
    def base_response(self):
        graphs_response = []
        for i in range(len(self.additional_response)):
            graphs_response.append({
                'name': '#chart_' + str(i) + ' svg',
                'data': self.additional_response[i],
                'measurement_point': self.measurement_point
            })
        response = {
            'graphs': graphs_response,
            'statistics': self.statistics
        }
        if self.active == 'map_':
            response.update(self.metadata)

        return response

    @cached_property
    def metadata(self):
        filter = Filters(use_header=self.logged_in)
        page = self.request.GET.get('active', 'startpage')
        uuid = self.request.session[page]['uuid']
        data = filter.from_timeseries_uuid(uuid) if uuid != "EMPTY" else {}
        return {
            'metadata': [
                {"name": "organisation",
                 "value": self.selected_organisation},
                {"name": "lithology", "value": str(data.get('lithology', '-'))},
                {"name": "surface-level", "value":
                    data.get('surface_level', '-')},
                {"name": "top-level", "value":
                    str(data.get('filter_top_level', '-'))},
                {"name": "bottom-level", "value":
                    str(data.get('filter_bottom_level', '-'))}
            ]
        }



class TimeSeriesDataView(BaseApiView):

    def get(self, request, *args, **kwargs):
        page = self.request.GET.get('active', 'startpage')
        response_dict = {
            'data': self.timeseries,
            'start': self.request.session[page]['start_js'],
            'end': self.request.session[page]['end_js'],
            'uuid': self.request.session[page]['uuid'],
            'name': self.request.session[page]['measurement_point']
        }
        return RestResponse(response_dict)


class MapDataView(BaseApiView):
    active = 'map_'

    def get(self, request, *args, **kwargs):
        page = self.request.GET.get('active')
        if page:
            self.set_session_value(page, 'measurement_point',
                       "Groundwater well: " + self.request.GET['name'])
            self.set_session_value(page, 'uuid', request.GET['uuid'])
            add_response = True
        else:
            add_response = False
        super().get(self, request, *args, **kwargs)
        datatypes = request.GET.get('datatypes', 'locations,timeseries_').split(
            ',')
        try:
            response_dict = {
                "result": {
                    x.strip('_'): getattr(self, x) for x in datatypes},
                "error": ""
            }
        except LizardApiError:
            response_dict = {
                "result": {},
                "error": "Too many groundwater locations to show on map. "
                         "Please zoom in."
            }
        if add_response:
            response_dict.update(self.base_response)
        return RestResponse(response_dict)

    @property
    def locations(self):
        locations = GroundwaterLocations(use_header=self.logged_in)
        south_west, north_east = self.coordinates
        locations.bbox(south_west=south_west,
                       north_east=north_east,
                       organisation=self.selected_organisation_id)
        return locations.coord_uuid_name()

    @property
    def timeseries_(self):
        gw_type, statistic = [
            x.strip(' ') for x in self.request.session['map_'].get(
                'dropdown_0', {'value': 'GWmBGS | mean'})['value'].split('|')
        ]
        timeseries = GroundwaterTimeSeries(use_header=self.logged_in)
        timeseries.queries = {
            "name": gw_type
        }
        south_west, north_east = self.coordinates
        timeseries.bbox(south_west=south_west,
                        north_east=north_east,
                        organisation=self.selected_organisation_id,
                        statistic=statistic,
                        **self.time_window)
        result = timeseries.ts_to_dict(
            start_date=jsdt.datestring_to_js(self.request.session['map_'][
                                                 'datepicker']['start']),
            end_date=jsdt.datestring_to_js(self.request.session['map_'][
                                               'datepicker']['end']),
            date_time='str'
        )
        return result

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
            self.series_to_js(
                npseries=self.pandas_timeseries,
                index=self.pandas_timeseries.index,
                key='Groundwaterlevels (m)',
                color='#1abc9c'
            ),
            self.series_to_js(
                npseries=self.selected_trend[0][0],
                index=self.pandas_timeseries.index,
                key='Detrended groundwaterlevels (m)'
            ),
            self.series_to_js(
                npseries=self.selected_trend[0][1],
                index=self.pandas_timeseries.index,
                key='Removed trend (m)',
                color='#f39c12'
            ),
        ])
        self.statistics = [self.selected_trend[0][3]]
        try:
            result.append([
                self.series_to_js(
                    npseries=self.selected_trend[0][0],
                    index=self.pandas_timeseries.index,
                    key='Detrended groundwaterlevels [step trend] (m)',
                    color='#1abc9c'
                ),
                self.series_to_js(
                    npseries=self.selected_trend[1][0],
                    index=self.pandas_timeseries.index,
                    key='Detrended groundwaterlevels [linear trend] (m)'
                ),
                self.series_to_js(
                    npseries=self.selected_trend[1][1],
                    index=self.pandas_timeseries.index,
                    key='Removed trend (m)',
                    color='#f39c12'
                ),
            ])
            self.statistics.append(self.selected_trend[0][3])
        except IndexError:
            pass
        return result


class FluctuationsDataView(BaseApiView):
    active = 'periodic_fluctuations'

    @cached_property
    def additional_response(self):
        return [[
            self.series_to_js(
                npseries=self.harmonic[3],
                index=[],
                key='Cumulative periodogram',
                dates=False
            )
        ], [
            self.series_to_js(
                npseries=self.selected_trend[-1][0],
                index=self.pandas_timeseries.index,
                key='Detrended groundwaterlevels (m)',
                color='#1abc9c'
            ),
            self.series_to_js(
                npseries=self.harmonic[0],
                index=self.pandas_timeseries.index,
                key='Groundwaterlevels with periodic fluctuations removed (m)'
            ),
            self.series_to_js(
                npseries=self.harmonic[1],
                index=self.pandas_timeseries.index,
                key='Harmonic series (m)',
                color='#f39c12'
            ),
        ]]


class RegressiveDataView(BaseApiView):
    active = 'autoregressive'

    @cached_property
    def additional_response(self):
        self.statistics = ["Akaike Information Criterion of the autoregressive "
                           "model is {:.2f}. Standard deviation of the "
                           "innovation (error) term is {:.2f}".format(
            self.autoregressive[3], self.autoregressive[4])]
        return [[
            self.series_to_js(
                npseries=self.correllogram,
                index=[],
                key='Correlogram',
                dates=False
            )
        ], [
            self.series_to_js(
                npseries=self.harmonic[0],
                index=self.pandas_timeseries.index,
                key='Groundwaterlevels with periodic fluctuations removed (m)',
                color='#1abc9c'
            ),
            self.series_to_js(
                npseries=self.autoregressive[0],
                index=self.pandas_timeseries.index,
                key='Residuals (m)'
            ),
            self.series_to_js(
                npseries=self.autoregressive[1],
                index=self.pandas_timeseries.index,
                key='AR (model)',
                color='#f39c12'
            ),
        ]]


class AdditiveDataView(BaseApiView):
    active = 'additive'

    @cached_property
    def additional_response(self):
        return [[
            self.timeseries,
            self.series_to_js(
                npseries=self.pandas_timeseries - self.autoregressive[0],
                index=self.pandas_timeseries.index,
                key='Modelled time series analysis (m)'
            )
        ]]


class FrequencyDataView(BaseApiView):
    active = 'frequency'

    @cached_property
    def additional_response(self):
        return [[
            self.series_to_js(
                npseries=self.harmonic[3],
                index=self.harmonic[4],
                key='Monitoring Frequency',
                dates=False
            )
        ]]


class DownloadAllView(BaseApiView):

    def get(self, request, *args, **kwargs):
        logger.debug('Downloading csv for %s', self.selected_organisation)
        ts = GroundwaterTimeSeries(use_header=self.logged_in)
        header, csv_ = ts.all_to_csv(
            organisation=self.selected_organisation_id)
        response = HttpResponse(content_type='text/csv')
        filename = slugify(self.selected_organisation)[:80] + \
                   "_ggmn_timeseries.csv"
        response['Content-Disposition'] = 'attachment; filename="' + \
                                          filename + '"'
        writer = csv.writer(response)
        writer.writerow(['uuid', 'name', 'location_name', 'x', 'y'])
        for row in header:
            writer.writerow(row)
        writer.writerow([])
        writer.writerow(['name', 'uuid', 'timestamp', 'value'])
        for row in csv_:
            writer.writerow(row)
        logger.debug('Wrote all data to csv-response, '
                     'filename of output csv is: %s', filename)
        return response


class MapFeatureInfoView(APIView):

    def get(self, request, *args, **kwargs):
        feature_info = RasterFeatureInfo()
        layername = request.GET.get('layername')
        if layername:
            extra_params = None
        else:
            extra_params = {
                param: request.GET.get(param.upper()) for param in (
                    "version", "format", "bbox", "height", "width", "layers",
                    "query_layers", 'x', 'y'
                )
            }
            layername = 'aquifers'

        response = feature_info.wms(lat=request.GET.get('lat'),
                                  lng=request.GET.get('lng'),
                                  layername=layername,
                                  extra_params=extra_params)
        return RestResponse(response)


class InterpolationLimits(APIView):

    def get(self, request, *args, **kwargs):
        raster_wms = RasterLimits()
        response = raster_wms.get_limits(
            layername=request.GET.get('layers'),
            bbox=request.GET.get('bbox')
        )
        if response == [[None, None]]:
            response = [[-1000, 1000]]
        return RestResponse(response)


class RestartMixin(object):

    def get(self, request, *args, **kwargs):
        bounds = request.session['map_']['bounds']
        self.instantiate_session()
        org_name = request.GET.get('name', False)
        org_uuid = request.GET.get('uuid', False)
        if org_name and org_uuid:
            request.session['map_']['bounds'] = bounds
            self.request.session['login']['selected_organisation'] = org_name
            self.request.session['login']['selected_organisation_id'] = org_uuid
            self.request.session.modified = True
        return super().get(request, *args, **kwargs)


class RegionalMapRestartView(RestartMixin, RegionalMapView):
    pass


class ReStartPageView(RestartMixin, StartPageView):
    pass


class GlobalRestartView(RestartMixin, GlobalView):
    pass
