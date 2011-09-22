#!/usr/bin/env python
"""
Parser for /etc/services file
"""

class ServiceError(Exception):
    def __str__(self):
        return self.args[0]

class ServiceList(dict):
    def __init__(self,path='/etc/services'):
        try:
            fd = open(path,'r')
            for l in open('/etc/services','r').readlines():
                if l.startswith('#'): 
                    continue
                try:
                    l = l[:l.index('#')]
                except ValueError:
                    pass

                try:
                    (name,target,aliases) =  map(lambda x: x.strip(), l.split(None,2))
                    names = [name] + aliases.split()
                except ValueError:
                    try:
                        (name,target) = map(lambda x: x.strip(), l.split(None,1))
                    except ValueError:
                        continue
                    names = [name]

                try:
                    (port,protocol) = target.split('/')
                    port = int(port)
                    protocol = protocol.upper()
                except ValueError:
                    continue

                if not self.has_key(port):
                    self[port] = {}
                self[port][protocol] = ServiceListEntry(port,protocol,names)

        except IOError,(ecode,emsg):
            raise ServiceError('Error reading %s: %s' % (path,emsg))
        except OSError,(ecode,emsg):
            raise ServiceError('Error reading %s: %s' % (path,emsg))
        
    def keys(self):
        return sorted(dict.keys(self))

    def items(self):
        return [(k,self[k]) for k in self.keys()] 

    def find(self,name=None,port=None,protocol=None):
        entries = []

        if port is not None:
            port = int(port)
        if protocol is not None:
            protocol = protocol.upper()

        if name is not None:
            if port is not None and protocol is not None:
                matches = self.find(port=port,protocol=protocol)
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
                if name in m.names:
                    entries.append(m)
            return entries

        elif port is not None:
            try:
                protocols = self[port]
            except ValueError:
                raise ValueError('Invalid port: %s' % port)
            except KeyError:
                return [] 
            if protocol is None:
                return protocols.values()
            try:
                return protocols[protocol]
            except KeyError:
                return []

        elif protocol is not None:
            for port,protocols in self.items():
                try:
                    entries.append(protocols[protocol])
                except KeyError:
                    continue 
            return entries 
        else:
            raise ValueError('No search terms given')

class ServiceListEntry(dict):
    """
    Class representing exactly one port,protocol pair from /etc/services
    """
    def __init__(self,port,protocol,names):
        self['port'] = int(port)
        self['protocol'] = protocol.upper()
        if type(names) in [list]:
            self['names'] = names
        else:
            self['names'] = [names]

    def __getattr__(self,item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError('No such ServiceListEntry item: %s' % item)

    def __repr__(self):
        return '%s/%s %s' % (self.port,self.protocol,','.join(self.names))

if __name__ == '__main__':
    import sys
    services = ServiceList()
    if len(sys.argv)==1:
        for port,s in services.items():
            print port, s
    else:
        for srv in sys.argv[1:]:
            for r in services.find(name=srv):
                print r

