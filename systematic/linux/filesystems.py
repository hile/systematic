#!/usr/bin/env python
"""
Implementation of linux filesystem mount point parsing
"""

import os,re,logging
from subprocess import Popen,PIPE

#noinspection PyPackageRequirements,PyPackageRequirements,PyPackageRequirements,PyPackageRequirements
from systematic.filesystems import MountPoint,FileSystemError

PSEUDO_FILESYSTEM = [
    'proc','sysfs','devpts',
    'fusectl','securityfs','debugfs',
    'rpc_pipefs','binfmt_misc','nfsd'
]

DM_PREFIX = '/dev/mapper/'
MAPPER_PATH = '/dev/mapper'

UUID_PATH = '/dev/disk/by-uuid'
LABEL_PATH = '/dev/disk/by-label'

class MountPoints(dict):
    """
    Mount points for linux filesystems
    """
    def __init__(self):
        dict.__init__(self)
        self.update()

    #noinspection PyMethodOverriding
    def update(self):
        """
        Update list of linux mountpoints based on /bin/mount output
        """
        p = Popen('/bin/mount',stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        #noinspection PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck
        if p.returncode != 0:
            raise FileSystemError('Error getting mountpoints: %s' % stderr)

        re_mount = re.compile(r'([^\s]*) on (.*) type ([^\s]+) \(([^\)]*)\)$')

        for l in stdout.split('\n'):
            if l == '': continue
            if l[:4] == 'map ': continue
            m = re.match(re_mount,l)
            if not m:
                continue
            device = m.group(1)
            mountpoint = m.group(2)
            filesystem = m.group(3)
            flags = map(lambda x: x.strip(), m.group(4).split(','))
            entry = LinuxMountPoint(device,mountpoint,filesystem)
            for f in flags:
                entry.flags.set(f,True)
            self[mountpoint] = entry

class LinuxMountPoint(MountPoint):
    """
    One linux mountpoint based on /bin/mount output line
    Additional attributes:
    uuid        Filesystem uuid
    label       Filesystem label
    """
    def __init__(self,device,mountpoint,filesystem):
        MountPoint.__init__(self,device,mountpoint,filesystem)

        if self.device[:len(DM_PREFIX)] == DM_PREFIX:
            for name in os.listdir(MAPPER_PATH):
                dev = os.path.realpath(os.path.join(MAPPER_PATH,name))
                if name == os.path.basename(self.device):
                    self.device = dev
                    break

        self.uuid = None
        for uuid in os.listdir(UUID_PATH):
            dev = os.path.realpath(os.path.join(UUID_PATH,uuid))
            if dev == self.device:
                self.uuid = uuid
                break

        self.label = None
        if os.path.isdir(LABEL_PATH):
            for label in os.listdir(LABEL_PATH):
                dev = os.path.realpath(os.path.join(LABEL_PATH,label))
                if dev == self.device:
                    self.label = label
                    break
        else:
            logging.debug('Missing directory: %s' % LABEL_PATH)

    def __getattr__(self,item):
        return MountPoint.__getattr__(self,item)

    def checkusage(self):
        """
        Function to parse usage of this filesystem
        """
        if self.filesystem in PSEUDO_FILESYSTEM:
            raise FileSystemError('%s: no usage data' % self.filesystem)
        p = Popen(['df','-k',self.mountpoint],stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        #noinspection PySimplifyBooleanCheck
        if p.returncode != 0:
            raise FileSystemError('Error running df: %s' % stderr)
    
        (header,usage) = stdout.split('\n',1)
        try:
            usage = ' '.join(usage.split('\n'))
        except ValueError:
            pass
        (fs,size,used,free,percent,mp) = map(lambda x: x.strip(), usage.split())
        percent = percent.rstrip('%')
        return {
            'size': long(size),'used': long(used), 
            'free': long(free),'percent': int(percent)
        }

