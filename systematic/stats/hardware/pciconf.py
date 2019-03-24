"""
FreeBSD pciconf parser

Parse pciconf -lv to get basic PCI bus and device info

Example usage:

from systematic.stats.hardware.pciconf import PCIConfClient
print(PCIConfClient().to_json())

"""

import json
import re

from systematic.stats import StatsParser, StatsParserError

RE_PCI_DEVICE = re.compile(r'^{0}$'.format(
    r'\s+'.join([
        r'(?P<driver>[^\@]+)@(?P<slot>[^\s]+):',
        r'class=(?P<device_class>[x0-9a-f]+)',
        r'card=(?P<card>[x0-9a-f]+)',
        r'chip=(?P<chip>[x0-9a-f]+)',
        r'rev=(?P<revision>[x0-9a-f]+)',
        r'hdr=(?P<header>[x0-9a-f]+)',
    ]))
)
# Report slots not attached to driver as None
RE_NO_DRIVER = re.compile(r'^none\d+$')


class PCIDevice(object):
    """PCI bus device

    """
    def __init__(self, driver, slot, device_class, card, chip, revision, header):
        self.slot = slot
        self.device_class = device_class
        self.card = card
        self.chip = chip
        self.revision = revision
        self.header = header

        # Filled later. Set defaults for entries with no data
        self.info = {
            'device': None,
            'vendor': None,
            'class': None,
            'subclass': None,
        }

        if RE_NO_DRIVER.match(driver):
            driver = None
        self.driver = driver

    def __repr__(self):
        return '{0} driver {1}'.format(self.slot, self.driver)

    def to_json(self):
        return {
            'slot': self.slot,
            'driver': self.driver,
            'class': self.device_class,
            'card': self.card,
            'chip': self.chip,
            'revision': self.revision,
            'header': self.header,
            'info': self.info,
        }


class PCIConfStats(StatsParser):
    """BSD pciconf stats

    """
    parser_name = 'pciconf'

    def __init__(self):
        super(PCIConfStats, self).__init__()
        self.devices = []

    def update(self):
        """Update PCI devices

        Updates list of PCI devices
        """
        self.devices = []
        stdout, stderr = self.execute('pciconf -lv')

        device = None
        for line in stdout.splitlines():

            m = RE_PCI_DEVICE.match(line)
            if m:
                device = PCIDevice(**m.groupdict())
                self.devices.append(device)

            elif device:
                try:
                    key, value = [v.strip() for v in line.strip().split('=')]
                    value = value.strip("'")
                    device.info[key] = value
                except ValueError:
                    raise StatsParserError('Error parsing line {0}'.format(line))

        return self.update_timestamp()

    def to_json(self, verbose=False):
        """Print device info as JSON

        """
        if self.__updated__ is None:
            self.update()

        return json.dumps(
            {
                'timestamp': self.__updated__,
                'devices': [device.to_json() for device in self.devices],
            },
            indent=2,
        )
