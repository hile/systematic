"""
Nginx stats

Parse OSS nginx stats from ngx_http_stub_status_module module.

Parsing of commercial version extended stats not supported.

Example nginx configuration to use with module defaults:

    server {
        listen 10061;
        location /nginx_status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
        }
    }

Example usage against this default config on localhost:

from systematic.stats.services.nginx import NginxStats
n=NginxStats('localhost')
print('{0:d} {1:d} {2:d}'.format(n.reading, n.writing, n.total_requests))
print(n.to_json())

"""

import json
import re
import requests
import time

from systematic.stats import StatsParser, StatsParserError

DEFAULT_HOST = 'localhost'
DEFAULT_REQUEST_PATH = '/nginx_status'
DEFAULT_STATS_PORT = 10061

# Do not fetch stats more often than this
DEFAULT_MINIMUM_INTERVAL = 0.2

RE_ACTIVE_CONNECTIONS = re.compile(r'^Active connections: (?P<count>\d+)\s*$')
RE_TOTAL_COUNTERS = re.compile(r'\s+(?P<accepted>\d+)\s(?P<handled>\d+)\s+(?P<total>\d+)\s*$')
RE_STAT_COUNTERS = re.compile(r'^Reading: (?P<reading>\d+)\s*Writing: (?P<writing>\d+)\sWaiting: (?P<waiting>\d+)\s*$')


class NginxStatsError(Exception):
    pass


class NginxStats(StatsParser):
    """Nginx stats client

    Client for default 'nginx stats' client.

    Minimum interval limits update requests frequency (float seconds)
    """
    parser_name = 'nginx'

    def __init__(self, host=DEFAULT_HOST, path=DEFAULT_REQUEST_PATH, schema='http',
                 port=DEFAULT_STATS_PORT, minimum_interval=DEFAULT_MINIMUM_INTERVAL):
        super(NginxStats, self).__init__('nginx')
        self.host = host
        self.path = path
        self.schema = schema
        if not path.startswith('/'):
            path = '/{0}'.format(path)
        self.port = port
        self.minimum_interval = minimum_interval

        self.__response__ = None
        self.__updated__ = None

    @property
    def url(self):
        return '{0}://{1}:{2}{3}'.format(self.schema, self.host, self.port, self.path)

    @property
    def data(self):
        """Get stats

        Stats are fetched max
        """
        if self.__response__ is not None and self.__updated__ is not None:
            now = time.time()
            if now - self.__updated__ <= self.minimum_interval:
                return self.__response__
            else:
                self.__updated__ = None
                self.__response__ = None

        try:
            res = requests.get(self.url)
            if res.status_code != 200:
                raise StatsParserError('Request returns status code {0}'.format(res.status_code))
            self.__response__ = res.content
            self.update_timestamp()
        except Exception as e:
            self.__updated__ = None
            self.__response__ = None
            raise StatsParserError('Error getting status {0}: {1}'.format(self.url, e))

        return self.__response__

    @property
    def active_connections(self):
        """Return number of active connections

        """
        for line in self.data.splitlines():
            m = RE_ACTIVE_CONNECTIONS.match(line)
            if m:
                try:
                    return int(m.groupdict()['count'])
                except ValueError:
                    raise StatsParserError('Invalid data for active connections')
        raise StatsParserError('Error checking active connections')

    @property
    def reading(self):
        """Return 'reading' counter

        """
        return self.stat_counter('reading')

    @property
    def writing(self):
        """Return 'writing' counter

        """
        return self.stat_counter('writing')

    @property
    def waiting(self):
        """Return 'waiting' counter

        """
        return self.stat_counter('waiting')

    @property
    def accepted_requests(self):
        """Return 'handled' summary counter

        """
        return self.total_counter('accepted')

    @property
    def handled_requests(self):
        """Return 'handled' summary counter

        """
        return self.total_counter('handled')

    @property
    def total_requests(self):
        """Return 'total' summary counter

        """
        return self.total_counter('total')

    def stat_counter(self, name):
        """Return stat counter

        Counter name is one of: reading, writing, waiting
        """
        for line in self.data.splitlines():
            m = RE_STAT_COUNTERS.match(line)
            if m:
                try:
                    return int(m.groupdict()[name])
                except KeyError:
                    raise StatsParserError('Unknown stat counter {0}'.format(name))
                except ValueError:
                    raise StatsParserError('Invalid data for stat counter {0}'.format(name))
        raise StatsParserError('Error checking stat counter {0}'.format(name))

    def total_counter(self, name):
        """Return total summary stat counter

        Counter name is one of: accepted, handled, total
        """
        for line in self.data.splitlines():
            m = RE_TOTAL_COUNTERS.match(line)
            if m:
                try:
                    return int(m.groupdict()[name])
                except KeyError:
                    raise StatsParserError('Unknown total counter {0}'.format(name))
                except ValueError:
                    raise StatsParserError('Invalid data for total counter {0}'.format(name))
        raise StatsParserError('Error checking total counter {0}'.format(name))

    def update(self):
        """Update data

        Trigger self.data property call to make sure we have current data
        """
        self.data
        return self.update_timestamp()

    def as_dict(self, verbose=False):
        """Return data as dict

        """
        if self.__updated__ is None:
            self.update()
        return {
            'server': {
                'host': self.host,
                'port': self.port,
                'url': self.url,
            },
            'timestamp': self.__updated__,
            'counters': {
                'active': {
                    'reading': self.reading,
                    'writing': self.writing,
                    'waiting': self.waiting,
                },
                'total': {
                    'accepted': self.accepted_requests,
                    'handled': self.handled_requests,
                    'requests': self.total_requests,
                },
            },
        }

    def to_json(self, verbose=False):
        """Return data as JSON

        """
        return json.dumps(self.as_dict(verbose=verbose), indent=2)
