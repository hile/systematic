#!/usr/bin/env python
"""
Process loading and unloading of SSH keys from user defined locations
automatically
"""

import sys,os,re
from subprocess import Popen,PIPE

SSHDIR = os.path.join(os.getenv('HOME'),'.ssh')
DEFAULT_CONFIG = os.path.join(SSHDIR,'sshkeys.conf')

re_keyinfo = re.compile('^(?P<bits>[0-9]+) (?P<fingerprint>[0-9a-f:]+) (?P<key_path>.*) \((?P<algorithm>[A-Z0-9-]+)\)$')

class SSHKeyError(Exception):
    def __str__(self):
        return self.args[0]

class UserSSHKeys(list):
    def __init__(self,keyconfig=DEFAULT_CONFIG):
        if keyconfig is not None:
            self.read_config(keyconfig)

    def read_config(self,keyconfig):
        self.keyconfig = keyconfig
        try:
            for l in [l.rstrip() for l in open(keyconfig,'r').readlines()]:
                self.append(SSHKeyFile(os.path.expandvars(os.path.expanduser(l))))
        except IOError,(ecode,emsg):
            raise SSHKeyError('Error loading %s: %s' % (keyconfig,emsg))
        except OSError,(ecode,emsg):
            raise SSHKeyError('Error loading %s: %s' % (keyconfig,emsg))

    def list_agent_keys(self):
        cmd = ['ssh-add','-l']
        p = Popen(cmd,stdin=PIPE,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        if p.returncode == 1:
            l = stdout.split('\n')[0].strip()
            if l == 'The agent has no identities.':
                return {} 
        if p.returncode != 0:
            raise SSHKeyError('Error listing SSH agent keys')

        keys = {}
        for l in [l.rstrip() for l in stdout.split('\n')[:-1]]:
            m = re_keyinfo.match(l)
            if not m:
                raise SSHKeyError('Error parsing agent key list line %s' % l)
            data = m.groupdict()
            keys[data['fingerprint']] = data
        return keys

class SSHKeyFile(object):
    def __init__(self,path):
        self.path = path
        self.available = False
        self.parse_public_key()

    def parse_public_key(self):
        public_key = '%s.pub' % self.path
        if not os.path.isfile(public_key):
            return

        cmd = ['ssh-keygen','-l','-f', public_key]
        p = Popen(cmd,stdin=PIPE,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        l = stdout.split('\n')[0].rstrip()
        if p.returncode != 0:
            return

        m = re_keyinfo.match(l)
        if not m:
            raise SSHKeyError(l)
        for k,v in m.groupdict().items():
            setattr(self,k,v)

        if os.path.isfile(self.path) and os.access(self.path,os.R_OK):
            self.available = True

    def __getattr__(self,attr):
        if attr in ['bits','fingerprint','algorithm']:
            if not hasattr(self,attr):
                self.parse_public_key()
            try:
                return self.__dict__[attr]
            except KeyError:
                return None
        raise AttributeError('No such SSHKeyFile attribute: %s' % attr) 

    def __repr__(self):
        return 'SSH key: %s' % self.path

    def load(self):
        cmd = ['ssh-add',self.path]
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()

if __name__ == '__main__':
    sk = UserSSHKeys()
    agent_fingerprints = sk.list_agent_keys().keys()
    for k in sk:
        if not k.available:
            continue
        if k.fingerprint not in agent_fingerprints:
            k.load()
        print k.algorithm,k.bits,k.fingerprint
 
