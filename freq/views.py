# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.views.generic.base import TemplateView

from freq import models


class BaseView(TemplateView):
    """Base view."""
    template_name = 'freq/base.html'
    title = _('FREQ - frequency analysis of groundwater measurements')
    page_title = _('FREQ - frequency analysis groundwater measurements')
    menu = [
        ('Startpage', 'Back to Homepage', 'startpage', 'active'),
        ('Detection of Trends', 'Step trend or flat trend detection',
         'trend_detection', 'disabled')
    ]
    measurement_point = 'No Time Series Selected'


class StartPageView(BaseView):
    template_name = 'freq/startpage.html'


class TrendDetectionView(BaseView):
    template_name = 'freq/trend_detection.html'


class PeriodicFluctuationsView(BaseView):
    template_name = 'freq/periodic_fluctuations.html'


class AutoRegressiveView(BaseView):
    template_name = 'freq/autoregressive.html'

