"""
Parse of SSH configuration files and keys
"""

import sys
import os
import pwd
import stat
import re
import string

from subprocess import Popen, PIPE
from systematic.log import Logger

SSH_CONFIG_FILES = ( 'authorized_keys', 'config', 'known_hosts', 'sshkeys.conf', )
DEFAULT_CONFIG = os.path.expanduser('~/.ssh/sshkeys.conf')
DEFAULT_AUTHORIZED_KEYS = os.path.expanduser('~/.ssh/authorized_keys')

SSH_DIR_PERMS = '0700'
SSH_FILE_PERMS = '0600'

# Lines for public keys
RE_PUBLIC_KEY_PATTERNS = (
    re.compile('^(?P<bits>\d+)\s+(?P<fingerprint>[^\s]+)\s+(?P<path>.*)\s+\((?P<algorithm>[^\s]+)\)$'),
)

class SSHKeyError(Exception):
    pass


def  parse_public_key_line_pattern(line):
    """Match public key lines to patterns

    Returns the match pattern as dict or None
    """
    for pattern in RE_PUBLIC_KEY_PATTERNS:
        m = pattern.match(line)
        if m:
            return m.groupdict()
    return None


class SSHKeyFile(dict):
    """
    Class for one SSH key. To be usable, the key's .pub public key file must be
    also available.

    Attribute autoload can be set to mark this key loaded with ssh-keys -a. It is
    also set, if key path is in ~/.ssh/sshkeys.conf.
    """
    def __init__(self, user_keys, path):
        self.log = Logger().default_stream
        self.user_keys = user_keys

        self.path = os.path.realpath(path)
        self.available = os.access(path, os.R_OK) and True or False

        self.autoload = False
        self.update({ 'bits': None, 'fingerprint': None, 'path': None, 'algorithm': None, })

        public_key = '{0}.pub'.format(self.path)
        if not os.path.isfile(public_key):
            self.available = False
            return

        cmd = ( 'ssh-keygen', '-l', '-f',  public_key )
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = [x.decode('utf-8') for x in p.communicate()]
        l = stdout.split('\n')[0].rstrip()

        if p.returncode != 0:
            raise SSHKeyError('ERROR parsing public key: {0}'.format(public_key))

        data = parse_public_key_line_pattern(l)
        if not data:
            raise SSHKeyError('Unsupported public key output: {0}'.format(l))

        for k, v in data.items():
            if k == 'path':
                k = 'public_key_path'
            self[k] = v

    def __repr__(self):
        return 'SSH key: {0}'.format(self.path)

    def __eq__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] == other

        for key in ( 'bits', 'fingerprint', 'algorithm', ):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] < other

        for key in ( 'bits', 'fingerprint', 'algorithm', ):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a < b

        return 0

    def __gt__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] > other

        for key in ( 'bits', 'fingerprint', 'algorithm', ):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a > b

        return 0

    def __le__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] <= other

        for key in ( 'bits', 'fingerprint', 'algorithm', ):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a <= b

        return 0

    def __ge__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] >= other

        for key in ( 'bits', 'fingerprint', 'algorithm', ):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a >= b

        return 0

    @property
    def is_loaded(self):
        loaded_keys = [x['path'] for x in self.user_keys.loaded_keys.values()]
        return self.path in loaded_keys and True or False

    def unload(self):
        """
        Unload this key from ssh-agent
        """
        cmd = ( 'ssh-add', '-d', self.path )
        p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()

    def load(self):
        """
        Load this key to ssh-agent. If passwords are requested, they are read
        from sys.stdin. Output is redirected to sys.stdout and sys.stderr.
        """
        cmd = ( 'ssh-add', self.path )
        p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()


class UserSSHKeys(dict):
    """
    List of user configured SSH keys to process
    """
    def __init__(self, authorized_keys=DEFAULT_AUTHORIZED_KEYS):
        self.log = Logger().default_stream
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

        paths = []
        for filename in os.listdir(user_sshdir):
            if filename in SSH_CONFIG_FILES or os.path.splitext(filename)[1] != '.pub':
                continue
            path = os.path.join(user_sshdir, filename)
            if os.path.isfile(path):
                paths.append(path)
        for path in paths:
            try:
                sshkey = SSHKeyFile(self, path)
            except SSHKeyError as e:
                self.log.debug(e)
                continue

            self[sshkey.path] = sshkey

    def read_config(self, path):
        """
        Read a key configuration file, containing list of keys outside
        ~/.ssh directory to process.
        """
        if not os.path.isfile(path):
            raise SSHKeyError('No such file: {0}'.format(path))

        try:
            for l in [l.rstrip() for l in open(path, 'r').readlines()]:
                sshkey = SSHKeyFile(self, os.path.expandvars(os.path.expanduser(l)))

                if sshkey.path not in self.keys():
                    self[sshkey.path] = sshkey

                self[sshkey.path].autoload = True

        except IOError as e:
            raise SSHKeyError('Error loading {0}: {1}'.format(path, e))
        except OSError as e:
            raise SSHKeyError('Error loading {0}: {1}'.format(path, e))

    @property
    def loaded_keys(self):
        """
        Return fingerprint, key mapping of keys loaded to ssh-agent
        """

        keys = {}

        cmd = ['ssh-add', '-l']
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = [x.decode('utf-8') for x in p.communicate()]

        if p.returncode == 1:
            l = stdout.split('\n')[0].strip()
            if l == 'The agent has no identities.':
                return keys

        if p.returncode != 0:
            raise SSHKeyError('Error listing loaded SSH agent keys')

        for l in [l.rstrip() for l in stdout.split('\n')[:-1]]:
            data = parse_public_key_line_pattern(l)
            if not data:
                raise SSHKeyError('Error parsing agent key list line {0}'.format(l))
            keys[data['fingerprint']] = data

        return keys

    @property
    def available(self):
        return [k for k in self.values() if k.available]

    def keys(self):
        """
        Return key filenames as sorted list
        """
        return sorted(super(UserSSHKeys, self).keys())

    def items(self):
        """
        Return (filename, key) value pairs sorted with self.keys()
        """
        return [(k, self[k]) for k in self.keys()]

    def values(self):
        """
        Return keys sorted with self.keys()
        """
        return [self[k] for k in self.keys()]

    def fix_permissions(self, directory_permissions=SSH_DIR_PERMS, file_permissions=SSH_FILE_PERMS):
        """
        Fix permissions in ~/.ssh to match permissions set by parameters. All files must be
        writable by user to use this function.

        Default values:
        directory_permissions   Directory permissions, by default '0700'
        file_permissions        File permissions, bt default '0600'
        """
        ssh_dir = os.path.expanduser('~/.ssh')
        dperm = int(directory_permissions, 8)
        fperm = int(file_permissions, 8)

        if not os.path.isdir(ssh_dir):
            self.log.debug('No such directory: {0}'.format(ssh_dir))
            return

        for (root, dirs, files) in os.walk(ssh_dir):
            if stat.S_IMODE(os.stat(root).st_mode) != dperm:
                self.log.debug('Fixing permissions for directory {0}'.format(root))
                os.chmod(root, dperm)

            for f in [os.path.join(root, f) for f in files]:
                if stat.S_IMODE(os.stat(f).st_mode) != fperm:
                    self.log.debug('Fixing permissions for file {0}'.format(f))
                    os.chmod(f, fperm)

    def load_keys(self, keys):
        """Load given keys

        Load given keys to SSH agent. Checks if key was already loaded and skips
        if it was. Keys can be either paths or SSHKeyFile instances.
        """
        paths = []
        for key in keys:
            if isinstance(key, SSHKeyFile):
                if not key.is_loaded:
                    paths.append(key.path)
            elif isinstance(key, str):
                paths.append(key)

        if paths:
            self.log.debug('Loading {0:d} keys to SSH agent'.format(len(paths)))
            cmd = [ 'ssh-add'] + paths
            p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
            p.wait()
        else:
            self.log.debug('All SSH keys were already loaded to SSH agent')

class OpenSSHPublicKey(dict):
    def __init__(self, line):
        self.line = line

        parts = line.split()

        if parts[0][0] in string.digits and len(parts) == 4:
            self['keyformat'] = 1
            self['bits'] = int(parts[0])
            self['exponent'] = parts[1]
            self['modulus'] = parts[2]
            self['comment'] = parts[3]
            self['options'] = None

        elif parts[0] in ( 'ssh-dsa', 'ssh-rsa', ):
            self['keyformat'] = 2
            self['keytype'] = parts[0]
            self['key_base64'] = parts[1]
            self['comment'] = len(parts) > 2 and parts[2] or ''
            self['options'] = None

        else:
            self['options'] = parts[0]
            parts = parts[1:]

            if not parts:
                raise SSHKeyError('error parsing openssh public key from {0}'.format(line))

            if parts[0] in ( 'ssh-dsa', 'ssh-rsa', ) and len(parts) ==  3:
                self['keyformat'] = 2
                self['keytype'] = parts[0]
                self['key_base64'] = parts[1]
                self['comment'] = parts[2]

            elif parts[0] in string.digits:
                self['keyformat'] = 1
                self['keyformat'] = 1
                self['bits'] = int(parts[0])
                self['exponent'] = parts[1]
                self['modulus'] = parts[2]
                self['comment'] = parts[3]

        if not self.keys():
            raise SSHKeyError('error parsing openssh public key from {0}'.format(line))

    def __repr__(self):
        return self.line


class AuthorizedKeys(list):
    """
    Parser for OpenSSH authorized_keys file contents
    """
    def __init__(self, path=DEFAULT_AUTHORIZED_KEYS):
        self.log = Logger().default_stream
        self.path = path
        self.load()

    def load(self):
        """
        Load authorized keys file, discarding earlier data in the object.

        SSH v1 authorized_keys line: options, bits, exponent, modulus, comment)
        SSH v2 authorized_keys line: options, keytype, base64-encoded key, comment)'

        See man sshd for details.
        """
        del self[0:len(self)]

        if not os.path.isfile(self.path):
            self.log.debug('No such file: {0}'.format(self.path))
            return

        for line in [l.rstrip() for l in open(self.path, 'r').readlines()]:
            if line.startswith('#') or line.strip() == '':
                continue

            try:
                self.append(OpenSSHPublicKey(line))
            except SSHKeyError:
                pass


class SSHConfigHost(dict):
    def __init__(self, config, name):
        self.config = config
        self.name = name

    def __repr__(self):
        return self.name

    def parse(self, line):
        try:
            key, value = [x.strip() for x in line.split(None, 1)]
            if key in ( 'Compression',  'ForwardAgent',  'ForwardX11',  'TCPKeepAlive', ):
                value = value == 'yes' and True or False

            if key in ('ServerAliveInterval', ):
                value = int(value)

            self[key] = value

        except ValueError:
            raise ValueError('Invalid line: {0}'.format(line))

    def __getattr__(self, attr):
        if attr in self.keys():
            return self[attr]

        raise AttributeError

    def __getitem__(self, item):
        if item in super(SSHConfigHost, self).keys():
            return super(SSHConfigHost, self).__getitem__(item)
        else:
            return self.config.defaults[item]

    @property
    def hostname(self):
        return 'HostName' in self.keys() and self['HostName'] or self.name

    @property
    def user(self):
        return 'User' in self.keys() and self['User'] or pwd.getpwuid(os.geteuid()).pw_name

    @property
    def forward_agent_enabled(self):
        if 'ForwardAgent' in self.keys():
            return self['ForwardAgent'].lower() in ['yes', True]
        else:
            # TODO - check default from system ssh_config
            return False

    @property
    def forward_x11_enabled(self):
        if 'ForwardX11' in self.keys():
            return self['ForwardX11'].lower() in ['yes', True]
        else:
            # TODO - check default from system ssh_config
            return False

    @property
    def tcp_keepalive_enabled(self):
        if 'TCPKeepAlive' in self.keys():
            return self['TCPKeepAlive'].lower() in ['yes', True]
        else:
            # TODO - check default from system ssh_config
            return False

    def keys(self):
        return sorted(list(super(SSHConfigHost, self).keys()) + list(self.config.defaults.keys()))

    def items(self):
        items = []
        for key in self.keys():
            if key in super(SSHConfigHost, self).keys():
                items.append((key, self[key]))
            else:
                items.append((key, self.config.defaults[key]))

        return items

    def values(self):
        items = []
        for key in self.keys():
            if key in super(SSHConfigHost, self).keys():
                items.append(self[key])
            else:
                items.append(self.config.defaults[key])

        return items


class SSHConfig(dict):
    def __init__(self, path=None):
        self.defaults = {}
        self.log = Logger().default_stream
        self.path = path is not None and path or os.path.expanduser('~/.ssh/config')
        self.reload()

    def reload(self):
        self.clear()
        if not os.path.isfile(self.path):
            self.log.debug('No such file: {0}'.format(self.path))
            return

        with open(self.path, 'r') as fd:
            host = None
            for l in [x.strip() for x in fd.readlines()]:
                if l=='' or l.startswith('#'):
                    continue

                if l[:5]=='Host ':
                    host = SSHConfigHost(self, l[5:])
                    self[host.name] = host

                else:
                    host.parse(l)

        if '*' in self.keys():
            self.defaults.update(self.pop('*').items())

    def keys(self):
        return [k for k in sorted(super(SSHConfig, self).keys())]

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def values(self):
        return [self[k] for k in self.keys()]
