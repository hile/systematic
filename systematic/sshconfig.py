#!/usr/bin/env python
"""
Process loading and unloading of SSH keys from user defined locations
automatically
"""

import sys,os,stat,re,string,logging
from subprocess import Popen,PIPE

# Configuration files we don't try to load as keys
SSH_CONFIG_FILES = [ 'authorized_keys', 'config', 'known_hosts', 'sshkeys.conf' ]
DEFAULT_CONFIG = os.path.expanduser('~/.ssh/sshkeys.conf')
DEFAULT_AUTHORIZED_KEYS = os.path.expanduser('~/.ssh/authorized_keys')

SSH_DIR_PERMS = '0700'
SSH_FILE_PERMS = '0600'

RE_KEYINFO = re.compile('^(?P<bits>[0-9]+) (?P<fingerprint>[0-9a-f:]+) (?P<path>.*) \((?P<algorithm>[A-Z0-9-]+)\)$')

class SSHKeyError(Exception):
    """
    Common exception thrown by classes in this module
    """
    def __str__(self):
        return self.args[0]

class UserSSHKeys(dict):
    """
    List of user configured SSH keys to process
    """
    def __init__(self,authorized_keys=DEFAULT_AUTHORIZED_KEYS):
        dict.__init__(self)
        self.log = logging.getLogger('modules')
        self.__parse_user_keyfiles()
        self.authorized_keys = AuthorizedKeys(authorized_keys)

    def __parse_user_keyfiles(self):
        """
        Parses any normal user keyfiles in ~/.ssh directory automatically.

        These keys are marked by default not to be automatically loaded:
        to enable, add key path to ~/.ssh/sshkeys.conf
        """
        user_sshdir = os.path.expanduser('~/.ssh')
        if not os.path.isdir(user_sshdir):
            return
        paths = filter(lambda x:
            os.path.isfile(x),
            [os.path.join(user_sshdir,x) for x in filter(lambda x:
                x not in SSH_CONFIG_FILES and os.path.splitext(x)[1]!='.pub',
                os.listdir(user_sshdir)
            )]
        )
        for path in paths:
            try:
                sshkey = SSHKeyFile(self,path)
            except SSHKeyError,emsg:
                self.log.debug(emsg)
                continue
            self[sshkey.path] = sshkey

    def read_config(self,path):
        """
        Read a key configuration file, containing list of keys outside
        ~/.ssh directory to process.
        """
        if not os.path.isfile(path):
            raise SSHKeyError('No such file: %s' % path)
        try:
            for l in [l.rstrip() for l in open(path,'r').readlines()]:
                sshkey = SSHKeyFile(self,os.path.expandvars(os.path.expanduser(l)))
                if sshkey.path not in self.keys():
                    self[sshkey.path] = sshkey
                self[sshkey.path].autoload = True
        except IOError,(ecode,emsg):
            raise SSHKeyError('Error loading %s: %s' % (path,emsg))
        except OSError,(ecode,emsg):
            raise SSHKeyError('Error loading %s: %s' % (path,emsg))

    def sshagent_loaded_keys(self):
        """
        Return list of fingerprints loaded to ssh-agent
        """
        keys = {}

        cmd = ['ssh-add','-l']
        p = Popen(cmd,stdin=PIPE,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        if p.returncode == 1:
            l = stdout.split('\n')[0].strip()
            if l == 'The agent has no identities.':
                return keys
        #noinspection PySimplifyBooleanCheck
        if p.returncode != 0:
            raise SSHKeyError('Error listing loaded SSH agent keys')

        for l in [l.rstrip() for l in stdout.split('\n')[:-1]]:
            m = RE_KEYINFO.match(l)
            if not m:
                raise SSHKeyError('Error parsing agent key list line %s' % l)
            data = m.groupdict()
            keys[data['fingerprint']] = data
        return keys

    def keys(self):
        """
        Return key filenames as sorted list
        """
        return sorted(dict.keys(self))

    def items(self):
        """
        Return (filename,key) value pairs sorted with self.keys()
        """
        return [(k,self[k]) for k in self.keys()]

    def values(self):
        """
        Return keys sorted with self.keys()
        """
        return [self[k] for k in self.keys()]

    def fix_permissions(self,directory_permissions=SSH_DIR_PERMS,file_permissions=SSH_FILE_PERMS):
        """
        Fix permissions in ~/.ssh to match permissions set by parameters. All files must be
        writable by user to use this function.

        Default values:
        directory_permissions   Directory permissions, by default '0700'
        file_permissions        File permissions, bt default '0600'
        """
        ssh_dir = os.path.expanduser('~/.ssh')
        dperm = int(directory_permissions,8)
        fperm = int(file_permissions,8)
        if not os.path.isdir(ssh_dir):
            self.log.debug('No such directory: %s' % ssh_dir)
            return
        for (root,dirs,files) in os.walk(ssh_dir):
            if stat.S_IMODE(os.stat(root).st_mode) != dperm:
                self.log.debug('Fixing permissions for directory %s' % root)
                os.chmod(root,dperm)
            for f in [os.path.join(root,f) for f in files]:
                if stat.S_IMODE(os.stat(f).st_mode) != fperm:
                    self.log.debug('Fixing permissions for file %s' % f)
                    os.chmod(f,fperm)


class SSHKeyFile(object):
    """
    Class for one SSH key. To be usable, the key's .pub public key file must be
    also available.

    Attribute autoload can be set to mark this key loaded with ssh-keys -a. It is
    also set, if key path is in ~/.ssh/sshkeys.conf.
    """
    def __init__(self,user_keys,path):
        self.user_keys = user_keys
        self.path = os.path.realpath(path)
        self.log = logging.getLogger('modules')
        self.available = os.access(path,os.R_OK) and True or False
        self.autoload = False
        self.parse_public_key()

    def parse_public_key(self):
        """
        Parse the public key file for this SSH key
        """
        public_key = '%s.pub' % self.path
        if not os.path.isfile(public_key):
            self.available = False
            return

        cmd = ['ssh-keygen','-l','-f', public_key]
        p = Popen(cmd,stdin=PIPE,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        l = stdout.split('\n')[0].rstrip()
        #noinspection PySimplifyBooleanCheck
        if p.returncode!=0:
            raise SSHKeyError('ERROR parsing public key: %s' % public_key)

        m = RE_KEYINFO.match(l)
        if not m:
            raise SSHKeyError('Unsupported public key output: %s' % l)
        for k,v in m.groupdict().items():
            if k=='path':
                k='public_key_path'
            setattr(self,k,v)

    def __getitem__(self,item):
        if item in ['path','bits','fingerprint','algorithm']:
            return getattr(self,item)
        raise KeyError('No such SSHKeyFile item: %s' % item)

    def __getattr__(self,attr):
        if attr in ['bits','fingerprint','algorithm']:
            if not hasattr(self,attr):
                self.parse_public_key()
            try:
                return self.__dict__[attr]
            except KeyError:
                return None
        if attr == 'is_loaded':
            agent_keys = self.user_keys.sshagent_loaded_keys()
            matches = filter(lambda x: x['fingerprint']==self.fingerprint, agent_keys.values())
            return len(matches) and True or False

        raise AttributeError('No such SSHKeyFile attribute: %s' % attr)

    def __repr__(self):
        return 'SSH key: %s' % self.path

    def unload(self):
        """
        Unload this key from ssh-agent
        """
        cmd = ['ssh-add','-d',self.path]
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()

    def load(self):
        """
        Load this key to ssh-agent. If passwords are requested, they are read
        from sys.stdin. Output is redirected to sys.stdout and sys.stderr.
        """
        cmd = ['ssh-add',self.path]
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()

class AuthorizedKeys(dict):
    """
    Parser for OpenSSH authorized_keys file contents
    """
    def __init__(self,path=DEFAULT_AUTHORIZED_KEYS):
        dict.__init__(self)
        self.log = logging.getLogger('modules')
        self.path = path
        self.load()

    def load(self):
        """
        Load authorized keys file, discarding earlier data in the object.

        SSH v1 authorized_keys line: options, bits, exponent, modulus, comment)
        SSH v2 authorized_keys line: options, keytype, base64-encoded key, comment)'

        See man sshd for details.
        """
        self.clear()
        if not os.path.isfile(self.path):
            self.log.debug('No such file: %s' % self.path)
            return

        for l in [l.rstrip() for l in open(self.path,'r').readlines()]:
            if l.startswith('#') or l.strip() == '':
                continue
            entry = {}
            parts = l.split()
            if parts[0][0] in string.digits and len(parts)==4:
                entry['keyformat'] = 1
                entry['bits'] = int(parts[0])
                entry['exponent'] = parts[1]
                entry['modulus'] = parts[2]
                entry['comment'] = parts[3]
                entry['options'] = None
            elif parts[0] in ['ssh-dsa','ssh-rsa']:
                entry['keyformat'] = 2
                entry['keytype'] = parts[0]
                entry['key_base64'] = parts[1]
                entry['comment'] = parts[2]
                entry['options'] = None
            else:
                entry['options'] = parts[0]
                parts = parts[1:]
                if parts[0] in ['ssh-dsa','ssh-rsa'] and len(parts)==3:
                    entry['keyformat'] = 2
                    entry['keytype'] = parts[0]
                    entry['key_base64'] = parts[1]
                    entry['comment'] = parts[2]
                elif parts[0] in string.digits:
                    entry['keyformat'] = 1
                    entry['keyformat'] = 1
                    entry['bits'] = int(parts[0])
                    entry['exponent'] = parts[1]
                    entry['modulus'] = parts[2]
                    entry['comment'] = parts[3]


            print entry

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    usk = UserSSHKeys()
    usk.fix_permissions()