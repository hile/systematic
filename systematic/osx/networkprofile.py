#!/usr/bin/env python
"""
Control and see status of OS/X network interfaces from python. 
"""

import logging,appscript

NETWORK_CONNECTION_TYPES = {
    'wlan':         2,
    'dialup':       3,  # Both bluetooth and USB 3G connections
    'ethernet':     5,
    'firewire':     8,
    'vpn':          10,
}

class NetworkConfigError(Exception):
    def __str__(self): 
        return self.args[0]

class NetworkProfileList(object):
    def __init__(self):
        try:
            self.app = appscript.app('System Events')
            self.location = self.app.network_preferences.get().current_location.get()
        except appscript.reference.CommandError,e:
            raise NetworkConfigError('Appscript initialization error: %s' % e.errormessage)

    def __getitem__(self,item):
        names = filter(
            lambda s: s.name.get()==item, self.location.services.get()
        )
        if len(names) == 0:
            raise KeyError('No such connection: %s' % item)
        try:
            return NetworkConnection(item,profiles=self)
        except appscript.reference.CommandError,e:
            raise KeyError('No such network service configured: %s' % item)

    def keys(self):
        return map(lambda s: s.name.get(), self.location.services.get())

    def items(self):
        return dict((
            s.name.get(), NetworkConnection(s.name.get(),profiles=self))
            for s in self.location.services.get()
        )

    def values(self):
        return dict(
            (NetworkConnection(s.name.get(),profiles=self))
            for s in self.location.services.get()
        )

    def filter(self,connection_type):
        try:
            connection_type = int(connection_type)
        except ValueError:
            try:
                connection_type = NETWORK_CONNECTION_TYPES[connection_type]
            except KeyError:
                raise NetworkConfigError(
                    'Unknown connection type: %s' % connection_type
                )
    
        return [    
            NetworkConnection(s.name.get(),self) 
            for s in filter(lambda s:
                s.kind.get()==connection_type, 
                self.location.services.get()
            )
        ]

class NetworkConnection(object):
    def __init__(self,name,profiles=None):
        if profiles is None:
            profiles = NetworkProfileList()
        self.name = name
        self.app = profiles.app

        names = filter(lambda s: 
            s.name.get()==name,
            profiles.location.services.get()
        )
        if len(names) == 0:
            raise NetworkConfigError('No such connection: %s' % name)
        try:
            self.connection = profiles.location.services[name].get()
        except KeyError,e:
            raise NetworkConfigError(str(e).strip("'"))

    def __repr__(self):
        return '%s %s: %s' % (
            self.connection_type,
            self.name,
            self.connected and 'connected' or 'not connected'
        )

    def __getattr__(self,item):
        if item.lower() in ['mac','mac_address']:
            item = 'MAC_address'

        if item in ['MAC_address','speed','mtu','duplex']:
            try:
                interface = self.connection.interface.get()
                return getattr(interface,item).get()
            except appscript.reference.CommandError,e:
                raise AttributeError(
                    'Value %s not available for interface %s' % (item,self.name)
                )

        if item == 'kind':
            try:
                return self.connection.kind.get()
            except appscript.reference.CommandError,e:
                raise NetworkConfigError(
                    'Error getting service type for %s' % self.name
                )

        if item == 'connection_type':
            kind = self.kind
            for k,v in NETWORK_CONNECTION_TYPES.items():
                if v == kind:
                     return k
            return 'unknown'    

        if item == 'connected':
            try:
                return self.connection.current_configuration.connected.get()
            except appscript.reference.CommandError,e:
                return False
        raise AttributeError('No such NetworkConnection attribute: %s' % item)

    def connect(self,password=None):
        """
        Connects the network interface. 
        
        If the interface is a VPN and it requires a password, you will still 
        get graphical password request dialog. Patches welcome how to enter 
        the passphrase with appscript.
        """
        if self.connected:
            raise NetworkConfigError('Already connected: %s' % self.name) 
        logging.info('Connecting to network profile: %s' % self.name)
        self.app.connect(self.connection)

    def disconnect(self):
        """
        Disconnect the network interface
        """
        if not self.connected:
            raise NetworkConfigError('Not connected: %s' % self.name) 
        logging.info('Disconnecting network profile: %s' % self.name)
        self.app.disconnect(self.connection)

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        print 'Usage: %s <network profile>' % sys.argv[0]
        sys.exit(1)
    n = NetworkProfileList()
    for ctype in sys.argv[1:]:
        print ctype, n.filter(ctype)

