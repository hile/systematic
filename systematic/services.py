"""
Parser for /etc/services file
"""

import os


class ServiceError(Exception):
    """
    Exceptions raised while parsing /etc/services file
    """
    pass


class ServiceListEntry(list):
    """
    Class representing exactly one port, protocol pair from /etc/services
    """
    def __init__(self, port, protocol, names):
        self.port = int(port)
        self.protocol = protocol.upper()
        if isinstance(names, str):
            self['names'] = [names]
        self.extend(names)

    def __repr__(self):
        return '{0}/{1} {2}'.format(self.port, self.protocol, ','.join(self))


class ServiceList(dict):
    """
    Dictionary of all services found in services file. Dictionary key is
    the port number, and each entry is dictionary with protocol name in
    uppercase pointing to a ServiceListEntry object.

    For example: ServiceList[22]['TCP']
    """
    def __init__(self, path='/etc/services'):
        if not os.path.isfile(path):
            raise ServiceError('No such file: {0}'.format(path))

        try:
            lines = open(path, 'r').readlines()
        except IOError as e:
            raise ServiceError('Error reading {0}: {1}'.format(path, e))
        except OSError as e:
            raise ServiceError('Error reading {0}: {1}'.format(path, e))

        for l in [l for l in lines if not l.startswith('#')]:
            try:
                l = l[:l.index('#')]
            except ValueError:
                pass

            try:
                name, target, aliases =  [x.strip() for x in l.split(None, 2)]
                names = [name] + aliases.split()
            except ValueError:
                try:
                    name, target = [x.strip() for x in l.split(None, 1)]
                except ValueError:
                    continue
                names = [name]

            try:
                port, protocol = target.split('/')
                port = int(port)
                protocol = protocol.upper()
            except ValueError:
                continue

            if port not in self:
                self[port] = {}
            self[port][protocol] = ServiceListEntry(port, protocol, names)

    def keys(self):
        """
        Return services sorted by name
        """
        return sorted(super(ServiceList, self).keys())

    def items(self):
        """
        Return (name, service) value pairs sorted by self.keys()
        """
        return [(k, self[k]) for k in self.keys()]

    def values(self):
        """
        Return services sorted by self.keys()
        """
        return [self[k] for k in self.keys()]

    def find(self, name=None, port=None, protocol=None):
        """
        Find service matching name, port or protocol
        """
        entries = []

        if port is not None:
            port = int(port)
        if protocol is not None:
            protocol = protocol.upper()

        if name is not None:
            if port is not None and protocol is not None:
                matches = self.find(port=port, protocol=protocol)
            elif port is not None:
                matches = self.find(port=port)
            elif protocol is not None:
                matches = self.find(protocol=protocol)
            else:
                matches = []
                for protocols in self.values():
                    for p in protocols.values():
                        matches.append(p)
            for m in matches:
                if name in m:
                    entries.append(m)
            return entries

        elif port is not None:
            try:
                protocols = self[port]
            except ValueError:
                raise ValueError('Invalid port: {0}'.format(port))
            except KeyError:
                return []
            if protocol is None:
                return protocols.values()
            try:
                return protocols[protocol]
            except KeyError:
                return []

        elif protocol is not None:
            for port, protocols in self.items():
                try:
                    entries.append(protocols[protocol])
                except KeyError:
                    continue
            return entries
        else:
            raise ValueError('No search terms given')

