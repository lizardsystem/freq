import copy
import datetime as dt
import json
import logging
from pprint import pprint  # left here for debugging purposes
from time import time
from time import sleep
import urllib

import numpy as np
import django.core.exceptions

from freq import jsdatetime
try:
    from django.conf import settings
    USR, PWD = settings.USR, settings.PWD
except django.core.exceptions.ImproperlyConfigured:
    print('WARNING: no USR and PWD found in settings. USR and PWD should have'
          'been set beforehand')
    USR = None
    PWD = None

# When you use this script stand alone, please set your login information here:
# USR = ******  # Replace the stars with your user name.
# PWD = ******  # Replace the stars with your password.


logger = logging.getLogger(__name__)


def join_urls(*args):
    return '/'.join(args)


class LizardApiError(Exception):
    pass


class Base(object):
    """
    Base class to connect to the different endpoints of the lizard-api.
    :param data_type: endpoint of the lizard-api one wishes to connect to.
    :param username: login username
    :param password: login password
    :param use_header: no login and password is send with the query when set
                       to False
    :param extra_queries: In case one wishes to set default queries for a
                          certain data type this is the plase.
    :param max_results:
    """
    username = USR
    password = PWD
    max_results = 1000

    @property
    def extra_queries(self):
        """
        Overwrite class to add queries
        :return: dictionary with extra queries
        """
        return {}

    def organisation_query(self, organisation, add_query_string='location__'):
        org_query = {}
        if isinstance(organisation, str):
            org_query.update({add_query_string + "organisation__unique_id":
                              organisation})
        elif organisation:
            org_query.update({
                add_query_string + "organisation__unique_id": ','.join(
                    org for org in organisation)
            })
        if org_query:
            return dict([urllib.parse.urlencode(org_query).split('=')])
        else:
            return {}

    def __init__(self, base="https://ggmn.lizard.net", use_header=False,
                 data_type=None):
        """
        :param base: the site one wishes to connect to. Defaults to the
                     Lizard ggmn production site.
        """
        if data_type:
            self.data_type = data_type
        self.use_header = use_header
        self.queries = {}
        self.results = []
        if base.startswith('http'):
            self.base = base
        else:
            self.base = join_urls('https:/', base)
            # without extra '/' ^^, this is added in join_urls
        self.base_url = join_urls(self.base, 'api/v2', self.data_type) + '/'

    def get(self, count=True, uuid=None, **queries):
        """
        Query the api.
        For possible queries see: https://nxt.staging.lizard.net/doc/api.html
        Stores the api-response as a dict in the results attribute.
        :param queries: all keyword arguments are used as queries.
        :return: a dictionary of the api-response.
        """
        if self.max_results:
            queries.update({'page_size': self.max_results, 'format': 'json'})
        queries.update(self.extra_queries)
        queries.update(getattr(self, "queries", {}))
        query = '?' + '&'.join(str(key) + '=' +
                               (('&' + str(key) + '=').join(value)
                               if isinstance(value, list) else str(value))
                               for key, value in queries.items())
        url = urllib.parse.urljoin(self.base_url, str(uuid)) if uuid else \
            self.base_url + query
        try:
            self.fetch(url)
        except urllib.error.HTTPError:  # TODO remove hack to prevent 420 error
            self.json = {'results': [], 'count': 0}
        try:
            logger.debug('Number found %s : %s with URL: %s', self.data_type,
                         self.json.get('count', 0), url)
        except (KeyError, AttributeError):
            logger.debug('Got results from %s with URL: %s',
                         self.data_type, url)
        self.parse()
        return self.results

    def fetch(self, url):
        """
        GETs parameters from the api based on an url in a JSON format.
        Stores the JSON response in the json attribute.
        :param url: full query url: should be of the form:
                    [base_url]/api/v2/[endpoint]/?[query_key]=[query_value]&...
        :return: the JSON from the response
        """
        if self.use_header:
            request_obj = urllib.request.Request(url, headers=self.header)
        else:
            request_obj = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(request_obj) as resp:
                encoding = resp.headers.get_content_charset()
                encoding = encoding if encoding else 'UTF-8'
                content = resp.read().decode(encoding)
                self.json = json.loads(content)
        except Exception:
            logger.exception("got error from: %s", url)
            raise

        return self.json

    def parse(self):
        """
        Parse the json attribute and store it to the results attribute.
        All pages of a query are parsed. If the max_results attribute is
        exceeded an ApiError is raised.
        """
        while True:
            try:
                if self.json['count'] > self.max_results:
                    raise LizardApiError(
                        'Too many results: {} found, while max {} are '
                        'accepted'.format(self.json['count'], self.max_results)
                    )
                self.results += self.json['results']
                next_url = self.json.get('next')
                if next_url:
                    self.fetch(next_url)
                else:
                    break
            except KeyError:
                self.results += [self.json]
                break
            except IndexError:
                break

    def parse_elements(self, element):
        """
        Get a list of a certain element from the root of the results attribute.
        :param element: the element you wish to get.
        :return: A list of all elements in the root of the results attribute.
        """
        self.parse()
        return [x[element] for x in self.results]

    @property
    def header(self):
        """
        The header with credentials for the api.
        """
        if self.use_header:
            return {
                "username": self.username,
                "password": self.password
            }
        return {}


class Organisations(Base):
    """
    Makes a connection to the organisations endpoint of the lizard api.
    """
    data_type = 'organisations'

    def all(self, organisation=None):
        """
        :return: a list of organisations belonging one has access to
                (with the credentials from the header attribute)
        """
        if organisation:
            self.get(unique_id=organisation)
        else:
            self.get()
        self.parse()
        return self.parse_elements('unique_id')


class Locations(Base):
    """
    Makes a connection to the locations endpoint of the lizard api.
    """

    def __init__(self, base="https://ggmn.lizard.net", use_header=False):
        self.data_type = 'locations'
        self.uuids = []
        super().__init__(base, use_header)

    def bbox(self, south_west, north_east, organisation=None):
        """
        Find all locations within a certain bounding box.
        returns records within bounding box using Bounding Box format (min Lon,
        min Lat, max Lon, max Lat). Also returns features with overlapping
        geometry.
        :param south_west: lattitude and longtitude of the south-western point
        :param north_east: lattitude and longtitude of the north-eastern point
        :return: a dictionary of the api-response.
        """
        min_lat, min_lon = south_west
        max_lat, max_lon = north_east
        coords = self.commaify(min_lon, min_lat, max_lon, max_lat)
        org_query = self.organisation_query(organisation, '')
        self.get(in_bbox=coords, **org_query)

    def distance_to_point(self, distance, lat, lon, organisation=None):
        """
        Returns records with distance meters from point. Distance in meters
        is converted to WGS84 degrees and thus an approximation.
        :param distance: meters from point
        :param lon: longtitude of point
        :param lat: latitude of point
        :return: a dictionary of the api-response.
        """
        coords = self.commaify(lon, lat)
        org_query = self.organisation_query(organisation, '')
        self.get(distance=distance, point=coords, **org_query)

    def commaify(self, *args):
        """
        :return: a comma-seperated string of the given arguments
        """
        return ','.join(str(x) for x in args)

    def coord_uuid_name(self):
        """
        Filters out the coordinates UUIDs and names of locations in results.
        Use after a query is made.
        :return: a dictionary with coordinates, UUIDs and names
        """
        result = {}
        for x in self.results:
            if x['uuid'] not in self.uuids:
                geom = x.get('geometry') or {}
                result[x['uuid']] = {
                        'coordinates': geom.get(
                            'coordinates', ['','']),
                        'name': x['name']
                }
                self.uuids.append(x['uuid'])
        return result


class TaskAPI(Base):
    data_type = 'tasks'

    def poll(self, url=None):
        logger.debug('TaskAPI', url)
        if url is None:
            return
        self.fetch(url)

    @property
    def status(self):
        try:
            logger.debug('Task status: %s', self.json.get("task_status"))
            status = self.json.get("task_status")
            if status is None:
                logger.debug('Task status: NONE')
                return "NONE"
            return status
        except AttributeError:
            logger.debug('Task status: NONE')
            return "NONE"

    def timeseries_csv(self, organisation, extra_queries_ts):
        if self.status != "SUCCESS":
            raise LizardApiError('Download not ready.')
        url = self.json.get("result_url")
        self.fetch(url)
        self.results = []
        self.parse()

        csv = (
            [result['name'], result['uuid'],
             jsdatetime.js_to_datestring(event['timestamp']), event['max']]
            for result in self.results for event in result['events']
        )
        loc = Locations(use_header=self.use_header)
        extra_queries = {
            key if not key.startswith("location__") else key[10:]: value
            for key, value in extra_queries_ts.items()
        }
        org_query = self.organisation_query(organisation, '')
        extra_queries.update(**org_query)
        loc.get(**extra_queries)
        coords = loc.coord_uuid_name()
        headers = (
            [
                r['uuid'], r['name'], coords[r['location']['uuid']]['name'],
                coords[r['location']['uuid']]['coordinates'][0],
                coords[r['location']['uuid']]['coordinates'][1]
            ]
            for r in self.results
        )
        return headers, csv


class TimeSeries(Base):
    """
    Makes a connection to the timeseries endpoint of the lizard api.
    """

    def __init__(self, base="https://ggmn.lizard.net", use_header=False):
        self.data_type = 'timeseries'
        self.uuids = []
        self.statistic = None
        super().__init__(base, use_header)

    def location_name(self, name, organisation=None):
        """
        Returns time series metadata for a location by name.
        :param name: name of a location
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        org_query = self.organisation_query(organisation)
        return self.get(location__name=name, **org_query)

    def location_uuid(self, loc_uuid, start='0001-01-01T00:00:00Z', end=None,
                      organisation=None):
        """
        Returns time series for a location by location-UUID.
        :param loc_uuid: name of a location
        :param start: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format, defaults to now
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        org_query = self.organisation_query(organisation)
        self.get(location__uuid=loc_uuid, **org_query)
        timeseries_uuids = [x['uuid'] for x in self.results]
        self.results = []
        for ts_uuid in timeseries_uuids:
            ts = TimeSeries(self.base, use_header=self.use_header)
            ts.uuid(ts_uuid, start, end, organisation)
            self.results += ts.results
        return self.results

    def uuid(self, ts_uuid, start='0001-01-01T00:00:00Z', end=None,
             organisation=None):
        """
        Returns time series for a timeseries by timeseries-UUID.
        :param ts_uuid: uuid of a timeseries
        :param start: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        if not end:
            end = jsdatetime.now_iso()
        old_base_url = self.base_url
        self.base_url += ts_uuid + "/"
        org_query = self.organisation_query(organisation)
        self.get(start=start, end=end, **org_query)
        self.base_url = old_base_url

    def start_csv_task(self, start='0001-01-01T00:00:00Z', end=None,
               organisation=None):
        if not end:
            end = jsdatetime.now_iso()
        if isinstance(start, int):
            start -= 10000
        if isinstance(end, int):
            end += 10000
        org_query = self.organisation_query(organisation)
        poll_url = self.get(
            start=start,
            end=end,
            async="true",
            format="json",
            **org_query
        )[0]['url']
        logger.debug("Async task url %s", poll_url)
        return poll_url, self.extra_queries

    def bbox(self, south_west, north_east, statistic=None,
             start='0001-01-01T00:00:00Z', end=None, organisation=None):
        """
        Find all timeseries within a certain bounding box.
        Returns records within bounding box using Bounding Box format (min Lon,
        min Lat, max Lon, max Lat). Also returns features with overlapping
        geometry.
        :param south_west: lattitude and longtitude of the south-western point
        :param north_east: lattitude and longtitude of the north-eastern point
        :param start_: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format
        :return: a dictionary of the api-response.
        """
        if not end:
            end = jsdatetime.now_iso()
        if isinstance(start, int):
            start -= 10000
        if isinstance(end, int):
            end += 10000

        min_lat, min_lon = south_west
        max_lat, max_lon = north_east

        polygon_coordinates = [
            [min_lon, min_lat],
            [min_lon, max_lat],
            [max_lon, max_lat],
            [max_lon, min_lat],
            [min_lon, min_lat],
        ]
        points = [' '.join([str(x), str(y)]) for x, y in polygon_coordinates]
        geom_within = {'a': 'POLYGON ((' + ', '.join(points) + '))'}
        geom_within = urllib.parse.urlencode(geom_within).split('=')[1]
        org_query = self.organisation_query(organisation)
        self.statistic = statistic
        if statistic == 'mean':
            statistic = ['count', 'sum']
        elif not statistic:
            statistic = ['min', 'max', 'count', 'sum']
            self.statistic = None
        elif statistic == 'range (max - min)':
            statistic = ['min', 'max']
        elif statistic == 'difference (last - first)':
            statistic = 'count'
        elif statistic == 'difference (mean last - first year)':
            year = dt.timedelta(days=366)
            first_end = jsdatetime.datetime_to_js(jsdatetime.js_to_datetime(start) + year)
            last_start = jsdatetime.datetime_to_js(jsdatetime.js_to_datetime(end) - year)
            self.get(
                start=start,
                end=first_end,
                min_points=1,
                fields=['count', 'sum'],
                location__geom_within=geom_within,
                **org_query
            )
            first_year = {}
            for r in self.results:
                try:
                    first_year[r['location']['uuid']] = {
                      'first_value_timestamp': r['first_value_timestamp'],
                      'mean': r['events'][0]['sum'] / r['events'][0]['count']
                    }
                except IndexError:
                    first_year[r['location']['uuid']] = {
                      'first_value_timestamp': np.nan,
                      'mean': np.nan
                    }
            self.results = []
            self.get(
                start=last_start,
                end=end,
                min_points=1,
                fields=['count', 'sum'],
                location__geom_within=geom_within,
                **org_query
            )
            for r in self.results:
                try:
                    r['events'][0]['difference (mean last - first year)'] = \
                        r['events'][0]['sum'] / r['events'][0]['count'] - \
                        first_year[r['location']['uuid']]['mean']
                    r['first_value_timestamp'] = \
                        first_year[
                            r['location']['uuid']]['first_value_timestamp']
                except IndexError:
                    r['events'] = [{
                        'difference (mean last - first year)': np.nan}]
                    r['first_value_timestamp'] = np.nan
                    r['last_value_timestamp'] = np.nan
            return

        self.get(
            start=start,
            end=end,
            min_points=1,
            fields=statistic,
            location__geom_within=geom_within,
            **org_query
        )

    def ts_to_dict(self, statistic=None, values=None,
                   start_date=None, end_date=None, date_time='js'):
        """
        :param date_time: default: js. Several options:
            'js': javascript integer datetime representation
            'dt': python datetime object
            'str': date in date format (dutch representation)
        """
        if len(self.results) == 0:
            self.response = {}
            return self.response
        if values:
            values = values
        else:
            values = {}
        if not statistic and self.statistic:
            statistic = self.statistic

        # np array with cols: 'min', 'max', 'sum', 'count', 'first', 'last'
        if not statistic:
            stats1 = ('min', 'max', 'sum', 'count')
            stats2 = (
                (0, 'min'),
                (1, 'max'),
                (2, 'mean'),
                (3, 'range (max - min)'),
                (4, 'difference (last - first)'),
                (5, 'difference (mean last - first year)')
            )
            start_index = 6
        else:
            if statistic == 'mean':
                stats1 = ('sum', 'count')
            elif statistic == 'range (max - min)':
                stats1 = ('min', 'max')
            else:
                stats1 = (statistic, )
            stats2 = ((0, statistic), )
            start_index = int(statistic == 'mean') + 1
        ts = []
        for result in self.results:
            try:
                timestamps = [int(result['first_value_timestamp']),
                              int(result['last_value_timestamp'])]
            except (ValueError, TypeError):
                timestamps = [np.nan, np.nan]
            except TypeError:
                # int(None)
                timestamps = [np.nan, np.nan]
            if not len(result['events']):
                y = 2 if statistic == 'difference (mean last - first year)' \
                    else 0
                ts.append(
                    [np.nan for _ in range(len(stats1) + y)] + timestamps)
            else:
                ts.append([float(result['events'][0][s]) for s in stats1] +
                          timestamps)
        npts = np.array(ts)
        if statistic:
            if statistic == 'mean':
                stat = (npts[:, 0] / npts[:, 1]).reshape(-1, 1)
            elif statistic == 'range (max - min)':
                stat = (npts[:, 1] - npts[:, 0]).reshape(-1, 1)
            elif statistic == 'difference (last - first)':
                stat = (npts[:, 1] - npts[:, 0]).reshape(-1, 1)
            else:
                stat = npts[:, 0].reshape(-1, 1)
            npts_calculated = np.hstack(
                (stat, npts[:, slice(start_index, -1)]))
        else:
            npts_calculated = np.hstack((
                npts[:, 0:2],
                (npts[:, 2] / npts[:, 3]).reshape(-1, 1),
                (npts[:, 1] - npts[:, 0]).reshape(-1, 1),

                npts[:, 4:]
            ))

        for i, row in enumerate(npts_calculated):
            location_uuid = self.results[i]['location']['uuid']
            loc_dict = values.get(location_uuid, {})
            loc_dict.update({stat: 'NaN' if np.isnan(row[i]) else row[i]
                             for i, stat in stats2})
            loc_dict['timeseries_uuid'] = self.results[i]['uuid']
            values[location_uuid] = loc_dict
        npts_min = np.nanmin(npts_calculated, 0)
        npts_max = np.nanmax(npts_calculated, 0)
        extremes = {
            stat: {
                'min': npts_min[i] if not np.isnan(npts_min[i]) else 0,
                'max': npts_max[i] if not np.isnan(npts_max[i]) else 0
            } for i, stat in stats2
        }
        dt_conversion = {
            'js': lambda x: x,
            'dt': jsdatetime.js_to_datetime,
            'str': jsdatetime.js_to_datestring
        }[date_time]
        if statistic != 'difference (mean last - first year)':
            start = dt_conversion(max(jsdatetime.round_js_to_date(start_date),
                                      jsdatetime.round_js_to_date(npts_min[-2])))
            end = dt_conversion(min(jsdatetime.round_js_to_date(end_date),
                                    jsdatetime.round_js_to_date(npts_max[-1])))
        else:
            start = dt_conversion(jsdatetime.round_js_to_date(start_date))
            end = dt_conversion(jsdatetime.round_js_to_date(end_date))
        self.response = {
            "extremes": extremes,
            "dates": {
                "start": start,
                "end": end
            },
            "values": values
        }
        return self.response


class GroundwaterLocations(Locations):
    """
    Makes a connection to the locations endpoint of the lizard api.
    Only selects GroundwaterStations.
    """

    @property
    def extra_queries(self):
        return {
            "object_type__model": 'filter'
        }


class GroundwaterTimeSeries(TimeSeries):
    """
    Makes a connection to the timeseries endpoint of the lizard api.
    Only selects GroundwaterStations.
    """

    @property
    def extra_queries(self):
        return {
            "location__object_type__model": 'filter'
        }


class GroundwaterTimeSeriesAndLocations(object):

    def __init__(self):
        self.locs = GroundwaterLocations()
        self.ts = GroundwaterTimeSeries()
        self.values = {}

    def bbox(self, south_west, north_east, start='0001-01-01T00:00:00Z',
             end=None, groundwater_type="GWmMSL"):
        if not end:
            self.end = jsdatetime.now_iso()
        else:
            self.end = end
        self.start = start
        self.ts.queries = {"name": groundwater_type}
        self.locs.bbox(south_west, north_east)
        self.ts.bbox(south_west=south_west, north_east=north_east,
                     start=start, end=self.end)

    def locs_to_dict(self, values=None):
        if values:
            self.values = values
        for loc in self.locs.results:
            self.values.get(loc['uuid'], {}).update({
                    'coordinates': loc['geometry']['coordinates'],
                    'name': loc['name']
                })
        self.response = self.values

    def results_to_dict(self):
        self.locs_to_dict()
        self.ts.ts_to_dict(values=self.values)
        return self.ts.response


class RasterFeatureInfo(Base):
    data_type = 'raster-aggregates'

    def wms(self, lat, lng, layername, extra_params=None):
        if 'igrac' in layername:
            self.base_url = "https://raster.lizard.net/wms"
            lat_f = float(lat)
            lng_f = float(lng)
            self.get(
                request="getfeatureinfo",
                layers=layername,
                width=1,
                height=1,
                i=0,
                j=0,
                srs="epsg:4326",
                bbox=','.join(
                    [lng, lat, str(lng_f+0.00001), str(lat_f+0.00001)]),
                index="world"
            )
            try:
                self.results = {"data": [self.results[1]]}
            except IndexError:
                self.results = {"data": ['null']}
        elif layername == 'aquifers':
            self.base_url = "https://ggis.un-igrac.org/geoserver/tbamap2015/wms"
            extra_params.update({
                'request': 'GetFeatureInfo',
                'service': 'WMS',
                'srs': 'EPSG:4326',
                'info_format': 'application/json'
            })
            self.get(**extra_params)
            self.results = {
                'data': self.results['features'][0]['properties']['aq_name']}
        else:
            self.get(
                agg='curve',
                geom='POINT(' + lng + '+' + lat + ')',
                srs='EPSG:4326',
                raster_names=layername,
                count=False
            )
        return self.results

    def parse(self):
        self.results = self.json


class RasterLimits(Base):
    data_type = 'wms'

    def __init__(self, base="https://raster.lizard.net",
                 use_header=False):
        super().__init__(base, use_header)
        self.base_url = join_urls(base, self.data_type)
        self.max_results = None

    def get_limits(self, layername, bbox):
        try:
            return self.get(
                request='getlimits',
                layers=layername,
                bbox=bbox,
                width=16,
                height=16,
                srs='epsg:4326'
            )
        except urllib.error.HTTPError:
            return [[-1000, 1000]]

    def parse(self):
        self.results = self.json


class Filters(Base):
    data_type = "filters"

    def from_timeseries_uuid(self, uuid):
        # We know the timeseries uuid. Timeseries are connected to locations
        # and the locations are connected to the filters that contain the
        # relevant information.

        # first get the location uuid from the timeseries.
        ts = Base(use_header=self.use_header, data_type='timeseries')
        location_data = ts.get(uuid=uuid)[0]['location']
        location_uuid = location_data.get('uuid')

        # surface_level is stored in the extra_metadata field of a location
        try:
            surface_level = str(location_data.get("extra_metadata")
                                .get("surface_level")) + " (m)"
        except AttributeError:
            surface_level = None

        # next get the location for the filter id
        location = Base(use_header=self.use_header, data_type='locations')
        try:
            filter_id = location.get(uuid=location_uuid)[0].get(
                'object').get('id')
        except TypeError:
            # the location doesn't connect to a filter, return empty
            return {}
        if filter_id:
            # next get and return the filter metadata
            gw_filter = Base(use_header=self.use_header, data_type='filters')
            result = gw_filter.get(uuid=filter_id)[0]
            result.update({
                "surface_level": surface_level
            })
            return result
        return {}


class Users(Base):
    data_type = "users"

    def get_organisations(self, username):
        self.get(username=username)
        if len(self.results) > 1 or len(self.results) == 0:
            if len(self.results):
                raise LizardApiError("Username is not unique")
            raise LizardApiError("Username not found")
        organisations_url = self.results[0].get("organisations_url")
        organisations = self.fetch(organisations_url)
        logger.debug('Found %d organisations for url: %s', len(organisations), organisations_url)
        return sorted(list(set(
            (org['name'], org['unique_id']) for org in organisations
        )))


if __name__ == '__main__':
    end = "1452470400000"
    start = "-2208988800000"
    start_time = time()
    GWinfo = GroundwaterTimeSeriesAndLocations()
    GWinfo.bbox(south_west=[-65.80277639340238, -223.9453125], north_east=[
        81.46626086056541, 187.3828125], start=start, end=end)
    x = GWinfo.results_to_dict()
    print(time() - start_time)
    pprint(x)
