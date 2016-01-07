__author__ = 'roel.vandenberg@nelen-schuurmans.nl'
"""
Collection of functions that transform
"""


import datetime as dt


JS_EPOCH = dt.datetime(1970, 1, 1)


def today():
    return dt.datetime.now().strftime('%d-%m-%Y')


def now_iso():
    """
    The date-timestamp of the moment now is called in ISO 8601 format.
    """
    return dt.datetime.now().isoformat().split('.')[0] + 'Z'


def datetime_to_js(date_time):
    if date_time is not None:
        return int((date_time - JS_EPOCH).total_seconds() * 1000)


def js_to_datetime(date_time):
    if date_time is not None:
        return JS_EPOCH + dt.timedelta(seconds=date_time/1000)


def js_to_datestring(js_date, iso=True):
    date_time = js_to_datetime(js_date)
    if iso:
        return date_time.strftime('%Y-%m-%d')
    else:
        return date_time.strftime('%d-%m-%Y')


def datestring_to_js(date_string, iso=True):
    if iso:
        date_time = dt.datetime.strptime(date_string, '%Y-%m-%d')
    else:
        date_time = dt.datetime.strptime(date_string, '%d-%m-%Y')
    return datetime_to_js(date_time)
