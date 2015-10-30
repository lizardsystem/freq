__author__ = 'roel.vandenberg@nelen-schuurmans.nl'

import datetime
import json
import requests


def join_urls(*args):
    return '/'.join(args)


class ApiError(Exception):
    pass


class Base(object):
    data_type = None
    username = 'dummy'
    password = 'dummy'
    use_header = False
    extra_queries = {}
    max_results = 1000

    def __init__(self, base="nxt.staging.lizard.net"):
        self.results = []
        if base.startswith('http'):
            self.base = base
        else:
            self.base = join_urls('https:/', base)
        self.base_url = join_urls(self.base, 'api/v2', self.data_type)

    def get(self, **queries):
        queries.update(self.extra_queries)
        query = '?' + '&'.join(key + '=' + value for key, value in
                               queries.items())
        url = join_urls(self.base_url, query)
        self.request(url)
        self.parse()
        return self.results

    def request(self, url):
        if self.use_header:
            response = requests.get(url, headers=self.header)
        else:
            response = requests.get(url)
        self.json = response.json()
        return self.json

    def post(self, UUID, data):
        post_url = join_urls(self.base_url, UUID, 'data')
        if self.use_header:
            requests.post(post_url, data=json.dumps(data), headers=self.header)
        else:
            requests.post(post_url, data=json.dumps(data))

    def parse(self):
        while True:
            try:
                if self.json['count'] > self.max_results:
                    raise ApiError('Too many results: {} found, while max {} '
                                   'are accepted'.format(
                        self.json['count'], self.max_results))
                self.results += self.json['results']
                next_url = self.json.get('next')
                if next_url:
                    self.request(next_url)
                else:
                    break
            except IndexError:
                break

    def parse_elements(self, element):
        self.parse()
        return [x[element] for x in self.results]

    @property
    def header(self):
        return {
            "username": self.username,
            "password": self.password
        }


class Organisations(Base):
    data_type = 'organisations'

    def all(self):
        self.get()
        self.parse()
        return self.parse_elements('unique_id')


class Locations(Base):
    data_type = 'locations'

    def __init__(self):
        self.uuids = []
        super().__init__()

    def in_bbox(self, x1, y1, x2, y2):
        coords = self.coord_string(x1, y1, x2, y2)
        self.get(in_bbox=coords)

    def distance_to_point(self, distance, x, y):
        coords = self.coord_string(x, y)
        self.get(distance=distance, point=coords)

    def coord_string(self, *args):
        return ','.join(str(x) for x in args)

    def coord_uuid_name(self):
        result = []
        for x in self.results:
            if x['uuid'] not in self.uuids:
                print(x['uuid'])
                result.append((x['geometry']['coordinates'], x['uuid'], x['name']))
                self.uuids.append(x['uuid'])
        return result


class TimeSeries(Base):
    data_type = 'timeseries'

    def location_name(self, name):
        self.get(location__name=name)

    def location_uuid(self, uuid):
        self.get(location__uuid=uuid)

    def uuid(self, uuid, start='0001-01-01T00:00:00', end=None):
        if not end:
            self.get(uuid=uuid, start=start)
        else:
            self.get(uuid=uuid, start=start, end=end)


class GroundwaterLocations(Locations):
    extra_queries = {"object_type\__model": "GroundwaterStation"}
