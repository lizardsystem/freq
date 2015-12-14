__author__ = 'roel.vandenberg@nelen-schuurmans.nl'

import datetime
import json
import requests
try:
    from freq.secretsettings import USR, PWD
except ImportError:
    print('WARNING: no secretsettings.py is found. USR and PWD should have been set '
          'beforehand')

## When you use this script stand alone, please set your login information here:
# USR = ******  # Replace the stars with your user name.
# PWD = ******  # Replace the stars with your password.


def join_urls(*args):
    return '/'.join(args)


class ApiError(Exception):
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
    data_type = None
    username = USR
    password = PWD
    use_header = True
    extra_queries = {}
    max_results = 100

    def __init__(self, base="nxt.staging.lizard.net"):
        """
        :param base: the site one wishes to connect to. Defaults to the
                     Lizard staging site.
        """
        self.results = []
        if base.startswith('http'):
            self.base = base
        else:
            self.base = join_urls('https:/', base) # without extra '/', this is
                                                   # added in join_urls
        self.base_url = join_urls(self.base, 'api/v2', self.data_type)

    def get(self, **queries):
        """
        Query the api.
        For possible queries see: https://nxt.staging.lizard.net/doc/api.html
        Stores the api-response as a dict in the results attribute.
        :param queries: all keyword arguments are used as queries.
        :return: a dictionary of the api-response.
        """
        queries.update(self.extra_queries)
        query = '?' + '&'.join(str(key) + '=' +
                               (('&' + str(key) + '=').join(value)
                               if isinstance(value, list) else str(value))
                               for key, value in queries.items())
        url = join_urls(self.base_url, query)
        self.fetch(url)
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
            response = requests.get(url, headers=self.header)
        else:
            response = requests.get(url)
        self.json = response.json()
        return self.json

    def post(self, UUID, data):
        """
        POST data to the api.
        :param UUID: UUID of the object in the database you wish to store
                     data to.
        :param data: Dictionary with the data to post to the api
        """
        post_url = join_urls(self.base_url, UUID, 'data')
        if self.use_header:
            requests.post(post_url, data=json.dumps(data), headers=self.header)
        else:
            requests.post(post_url, data=json.dumps(data))

    def parse(self):
        """
        Parse the json attribute and store it to the results attribute.
        All pages of a query are parsed. If the max_results attribute is
        exceeded an ApiError is raised.
        """
        while True:
            try:
                if self.json['count'] > self.max_results:
                    raise ApiError('Too many results: {} found, while max {} '
                                   'are accepted'.format(
                        self.json['count'], self.max_results))
                self.results += self.json['results']
                next_url = self.json.get('next')
                if next_url:
                    self.fetch(next_url)
                else:
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
        return {
            "username": self.username,
            "password": self.password
        }

    @property
    def now(self):
        """
        The date-timestamp of the moment now is called in ISO 8601 format.
        """
        return datetime.datetime.now().isoformat().split('.')[0] + 'Z'


class Organisations(Base):
    """
    Makes a connection to the organisations endpoint of the lizard api.
    """
    data_type = 'organisations'

    def all(self):
        """
        :return: a list of organisations belonging one has access to
                (with the credentials from the header attribute)
        """
        self.get()
        self.parse()
        return self.parse_elements('unique_id')


class Locations(Base):
    """
    Makes a connection to the locations endpoint of the lizard api.
    """
    data_type = 'locations'

    def __init__(self):
        self.uuids = []
        super().__init__()

    def in_bbox(self, min_lon, min_lat, max_lon, max_lat):
        """
        Find all locations within a certain bounding box.
        returns records within bounding box using Bounding Box format (min Lon,
        min Lat, max Lon, max Lat). Also returns features with overlapping
        geometry.
        :param min_lon: longtitude of the upper left point
        :param min_lat: latitude of the upper left point
        :param max_lon: longtitude of the lower right point
        :param max_lat: latitude of the lower right point
        :return: a dictionary of the api-response.
        """
        coords = self.commaify(min_lon, min_lat, max_lon, max_lat)
        self.get(in_bbox=coords)

    def distance_to_point(self, distance, lon, lat):
        """
        Returns records with distance meters from point. Distance in meters
        is converted to WGS84 degrees and thus an approximation.
        :param distance: meters from point
        :param lon: longtitude of point
        :param lat: latitude of point
        :return: a dictionary of the api-response.
        """
        coords = self.commaify(lon, lat)
        self.get(distance=distance, point=coords)

    def commaify(self, *args):
        """
        :return: a comma-seperated string of the given arguments
        """
        return ','.join(str(x) for x in args)

    def coord_uuid_name(self):
        """
        Filters out the coordinates UUIDs and names of the locations in results.
        Use after a query is made.
        :return: a dictionary with coordinates, UUIDs and names
        """
        result = []
        for x in self.results:
            if x['uuid'] not in self.uuids:
                result.append(
                    (x['geometry']['coordinates'], x['uuid'], x['name']))
                self.uuids.append(x['uuid'])
        return result


class TimeSeries(Base):
    """
    Makes a connection to the timeseries endpoint of the lizard api.
    """
    data_type = 'timeseries'

    def location_name(self, name):
        """
        Returns time series metadata for a location by name.
        :param name: name of a location
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        return self.get(location__name=name)

    def location_uuid(self, uuid, start='0001-01-01T00:00:00Z', end=None):
        """
        Returns time series for a location by location-UUID.
        :param uuid: name of a location
        :param start: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format, defaults to now
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        self.get(location__uuid=uuid)
        timeseries_uuids = [x['uuid'] for x in self.results]
        self.results = []
        print('timeseries_uuids', timeseries_uuids, start, end)
        for uuid in timeseries_uuids:
            ts = TimeSeries(self.base)
            ts.uuid(uuid, start, end)
            self.results += ts.results
        return self.results

    def uuid(self, uuid, start='0001-01-01T00:00:00Z', end=None):
        """
        Returns time series for a location by location-UUID.
        :param uuid: name of a location
        :param start: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format
        :return: a dictionary of with nested location, aquo quantities and
                 events.
        """
        if not end:
            end = self.now
        self.get(uuid=uuid, start=start, end=end)

    def from_bbox(self, min_lon, min_lat, max_lon, max_lat,
                  start='0001-01-01T00:00:00Z', end=None):
        """
        Find all timeseries within a certain bounding box.
        Returns records within bounding box using Bounding Box format (min Lon,
        min Lat, max Lon, max Lat). Also returns features with overlapping
        geometry.
        :param min_lon: longtitude of the upper left point
        :param min_lat: latitude of the upper left point
        :param max_lon: longtitude of the lower right point
        :param max_lat: latitude of the lower right point
        :param start: start timestamp in ISO 8601 format
        :param end: end timestamp in ISO 8601 format
        :return: a dictionary of the api-response.
        """
        if not end:
            end = self.now

        polygon_coordinates = [
            [min_lon, min_lat],
            [min_lon, max_lat],
            [max_lon, max_lat],
            [max_lon, min_lat],
            [min_lon, min_lat],
        ]
        points = [' '.join([str(x), str(y)]) for x, y in polygon_coordinates]
        geom_within = 'POLYGON ((' + ', '.join(points) + '))'
        self.get(start=start, end=end, min_points=1, fields=[
            'count', 'sum', 'min', 'max'], location__geom_within=geom_within)


class GroundwaterLocations(Locations):
    """
    Makes a connection to the locations endpoint of the lizard api.
    Only selects GroundwaterStations.
    """
    extra_queries = {"object_type\__model": "GroundwaterStation"}
