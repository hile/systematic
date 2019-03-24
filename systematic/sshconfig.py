"""
Parse of SSH configuration files and keys
"""

import sys
import os
import pwd
import stat
import re
import string
import tempfile

from builtins import str
from subprocess import Popen, PIPE
from systematic.log import Logger

SSH_CONFIG_FILES = ('authorized_keys', 'config', 'known_hosts', 'sshkeys.conf')
DEFAULT_CONFIG = os.path.expanduser('~/.ssh/sshkeys.conf')
DEFAULT_AUTHORIZED_KEYS = os.path.expanduser('~/.ssh/authorized_keys')
DEFAULT_KNOWN_HOSTS = os.path.expanduser('~/.ssh/known_hosts')

SSH_DIR_PERMS = '0700'
SSH_FILE_PERMS = '0600'

# Lines for public keys
RE_PUBLIC_KEY_PATTERNS = (
    re.compile(r'^(?P<bits>\d+)\s+(?P<fingerprint>[^\s]+)\s+(?P<path>.*)\s+\((?P<algorithm>[^\s]+)\)$'),
)


class SSHKeyError(Exception):
    pass


def parse_public_key_line_pattern(line):
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
        self.update({'bits': None, 'fingerprint': None, 'path': None, 'algorithm': None})

        public_key = '{}.pub'.format(self.path)
        if not os.path.isfile(public_key):
            self.available = False
            return

        cmd = ('ssh-keygen', '-l', '-f',  public_key)
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = [str(x, 'utf-8') for x in p.communicate()]
        line = stdout.split('\n')[0].rstrip()

        if p.returncode != 0:
            raise SSHKeyError('ERROR parsing public key: {}'.format(public_key))

        data = parse_public_key_line_pattern(line)
        if not data:
            raise SSHKeyError('Unsupported public key output: {}'.format(line))

        for k, v in data.items():
            if k == 'path':
                k = 'public_key_path'
            self[k] = v

    def __repr__(self):
        return 'SSH key: {}'.format(self.path)

    def __eq__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] == other

        for key in ('bits', 'fingerprint', 'algorithm'):
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

        for key in ('bits', 'fingerprint', 'algorithm'):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a < b

        return 0

    def __gt__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] > other

        for key in ('bits', 'fingerprint', 'algorithm'):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a > b

        return 0

    def __le__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] <= other

        for key in ('bits', 'fingerprint', 'algorithm'):
            a = getattr(self, key)
            b = getattr(other, key)
            if a != b:
                return a <= b

        return 0

    def __ge__(self, other):
        if isinstance(other, str):
            return self['fingerprint'] >= other

        for key in ('bits', 'fingerprint', 'algorithm'):
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
        cmd = ('ssh-add', '-d', self.path)
        p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()

    def load(self):
        """
        Load this key to ssh-agent. If passwords are requested, they are read
        from sys.stdin. Output is redirected to sys.stdout and sys.stderr.
        """
        cmd = ('ssh-add', self.path)
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
            raise SSHKeyError('No such file: {}'.format(path))

        try:
            for l in [l.rstrip() for l in open(path, 'r').readlines()]:
                sshkey = SSHKeyFile(self, os.path.expandvars(os.path.expanduser(l)))

                if sshkey.path not in self.keys():
                    self[sshkey.path] = sshkey

                self[sshkey.path].autoload = True

        except IOError as e:
            raise SSHKeyError('Error loading {}: {}'.format(path, e))
        except OSError as e:
            raise SSHKeyError('Error loading {}: {}'.format(path, e))

    @property
    def loaded_keys(self):
        """
        Return fingerprint, key mapping of keys loaded to ssh-agent
        """

        keys = {}

        cmd = ['ssh-add', '-l']
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = [str(x, 'utf-8') for x in p.communicate()]

        if p.returncode == 1:
            line = stdout.split('\n')[0].strip()
            if line == 'The agent has no identities.':
                return keys

        if p.returncode != 0:
            raise SSHKeyError('Error listing loaded SSH agent keys')

        for line in [line.rstrip() for line in stdout.split('\n')[:-1]]:
            data = parse_public_key_line_pattern(line)
            if not data:
                raise SSHKeyError('Error parsing agent key list line {}'.format(line))
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
            self.log.debug('No such directory: {}'.format(ssh_dir))
            return

        for (root, _dirs, files) in os.walk(ssh_dir):
            if stat.S_IMODE(os.stat(root).st_mode) != dperm:
                self.log.debug('Fixing permissions for directory {}'.format(root))
                os.chmod(root, dperm)

            for f in [os.path.join(root, f) for f in files]:
                if stat.S_IMODE(os.stat(f).st_mode) != fperm:
                    self.log.debug('Fixing permissions for file {}'.format(f))
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
            cmd = ['ssh-add'] + paths
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

        elif parts[0] in ('ssh-dsa', 'ssh-rsa'):
            self['keyformat'] = 2
            self['keytype'] = parts[0]
            self['key_base64'] = parts[1]
            self['comment'] = len(parts) > 2 and parts[2] or ''
            self['options'] = None

        else:
            self['options'] = parts[0]
            parts = parts[1:]

            if not parts:
                raise SSHKeyError('error parsing openssh public key from {}'.format(line))

            if parts[0] in ('ssh-dsa', 'ssh-rsa') and len(parts) == 3:
                self['keyformat'] = 2
                self['keytype'] = parts[0]
                self['key_base64'] = parts[1]
                self['comment'] = parts[2]

            elif parts[0] in string.digits:
                self['keyformat'] = 1
                self['bits'] = int(parts[0])
                self['exponent'] = parts[1]
                self['modulus'] = parts[2]
                self['comment'] = parts[3]

        if not self.keys():
            raise SSHKeyError('error parsing openssh public key from {}'.format(line))

    def __eq__(self, other):
        for attr in ('keyformat', 'keytype' 'bits', 'exponent', 'modulus', 'key_base64'):
            a = self.get(attr, None)
            b = other.get(attr, None)
            if a is None and b is None:
                continue
            if (a is not None and b is None) or (a is None and b is not None):
                return False
            if a != b:
                return False
        return True

    def __repr__(self):
        return self.line

    def fingerprint(self, fingerprint_hash=None):
        """Key fingerprint

        Return key fingerprint with ssh-keygen
        """
        try:
            fd, name = tempfile.mkstemp(prefix='sshkey-')
            with open(name, 'w') as fd:
                fd.write('{}'.format(self.line))
            if fingerprint_hash:
                p = Popen(('ssh-keygen', '-E', fingerprint_hash, '-lf', name), stdin=PIPE, stdout=PIPE, stderr=PIPE)
            else:
                p = Popen(('ssh-keygen', '-lf', name), stdin=PIPE, stdout=PIPE, stderr=PIPE)
            stdout, stderr = [str(v, 'utf-8') for v in p.communicate()]
            if p.returncode != 0:
                raise SSHKeyError('Error running ssh-keygen: returns {}'.format(p.returncode))
            os.unlink(name)
            return stdout.rstrip().split()[1].split(':', 1)[1]
        except Exception as e:
            raise SSHKeyError('Error getting fingerprint for {}: {}'.format(self.line, e))

    def as_dict(self):
        """
        Return SSH key details as dictionary
        """
        data = self.copy()
        data['fingerprint'] = self.fingerprint()
        return data


class KnownHostsHost(object):
    """
    Host in known hosts file
    """
    def __init__(self, host):
        self.host = host
        self.type_sort_key, self.sort_value, self.type = self.__detect_type__(host)

    def __detect_type__(self, value):
        """
        Detect host type (hostname, ipv4_address, ipv6_address)
        """
        def is_ipv6_address(value):
            try:
                value, interface = value.split('%', 1)
            except:  # noqa
                pass
            try:
                parts = value.split(':')
                for part in parts:
                    if part == '':
                        continue
                    part = int(part, 16)
                    if part < 0:
                        raise ValueError
                return True
            except Exception:
                return False

        def is_ipv4_address(value):
            try:
                value, interface = value.split('%', 1)
            except:  # noqa
                pass
            try:
                parts = value.split('.', 3)
                for part in parts:
                    part = int(part)
                    if part < 0 or part > 255:
                        raise ValueError
                return True
            except:  # noqa
                return False

        # Strip port
        if value.startswith('['):
            value = value[1:]
            try:
                value, port = value.split(':', 1)
            except:  # noqa
                pass

        if value.endswith(']'):
            value = value[:-1]

        if is_ipv4_address(value):
            return 1, value, 'ipv4_address'

        elif is_ipv6_address(value):
            return 2, value, 'ipv6_address'

        else:
            return 0, value, 'hostname'

    def __repr__(self):
        return '{} {}'.format(self.type, self.host)

    def __str__(self):
        return self.host

    def __eq__(self, other):
        if isinstance(other, str):
            return self.host == other
        for attr in ('type_sort_key', 'sort_value', ):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, str):
            return self.host < other
        for attr in ('type_sort_key', 'sort_value', ):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a < b
        return True

    def __gt__(self, other):
        if isinstance(other, str):
            return self.host > other
        for attr in ('type_sort_key', 'sort_value', ):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a > b
        return True

    def __le__(self, other):
        if isinstance(other, str):
            return self.host <= other
        for attr in ('type_sort_key', 'sort_value', ):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a <= b
        return True

    def __ge__(self, other):
        if isinstance(other, str):
            return self.host >= other
        for attr in ('type_sort_key', 'sort_value', ):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a >= b
        return True


class KnownHostsEntry(object):
    """
    Key entry in known_hosts file. Merges unique key to hostnames.
    """
    def __init__(self, line):
        self.__hosts__ = []
        self.keytype, self.fingerprint = line.split(None, 1)

    def __str__(self):
        return '{} {} {}'.format(
            self.hosts,
            self.keytype,
            self.fingerprint
        )

    def __repr__(self):
        return '{} {}'.format(self.keytype, self.fingerprint)

    def __eq__(self, other):
        for attr in ('keytype', 'fingerprint'):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        for attr in ('keytype', 'fingerprint'):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a > b
        return 0

    def __lt__(self, other):
        for attr in ('keytype', 'fingerprint'):
            a = getattr(self, attr)
            b = getattr(other, attr)
            if a != b:
                return a < b

    @property
    def hosts(self):
        return ','.join('{}'.format(host) for host in sorted(self.__hosts__))

    def add_hosts(self, hosts):
        """Add hosts to key

        """
        for host in hosts:
            if host not in self.__hosts__:
                self.__hosts__.append(KnownHostsHost(host))


class KnownHosts(list):
    """
    Parser for OpenSSH known_hosts file contents
    """
    def __init__(self, path=DEFAULT_KNOWN_HOSTS, fingerprint_hash=None):
        self.log = Logger().default_stream
        self.path = path
        self.fingerprint_hash = fingerprint_hash
        self.load()

    def load(self):
        """
        Load known hosts file, discarding earlier data in the object.
        """
        del self[0:len(self)]

        if not os.path.isfile(self.path):
            self.log.debug('No such file: {}'.format(self.path))
            return

        for line in [l.rstrip() for l in open(self.path, 'r').readlines()]:
            if line.startswith('#') or line.strip() == '':
                continue

            # Strip list of hosts from line
            hosts, key = line.split(None, 1)
            hosts = hosts.split(',')

            try:
                key = KnownHostsEntry(key)
                if key not in self:
                    self.append(key)
                else:
                    key = self[self.index(key)]
                key.add_hosts(hosts)
            except SSHKeyError:
                pass

    def save(self, path=None):
        """Save known hosts

        Saves known hosts file, merging same keys to single line
        """
        if path is None:
            path = self.path
        try:
            with open(path, 'w') as fd:
                for entry in self:
                    fd.write('{}\n'.format(entry))
        except Exception as e:
            raise SSHKeyError('Error writing {}: {}'.format(path, e))

    def find_host_key(self, value):
        """Find key for hostname

        """
        for key in self:
            if value in key.hosts:
                return key
        return None


class AuthorizedKeys(list):
    """
    Parser for OpenSSH authorized_keys file contents
    """
    def __init__(self, path=DEFAULT_AUTHORIZED_KEYS, fingerprint_hash=None):
        self.log = Logger().default_stream
        self.path = path
        self.fingerprint_hash = fingerprint_hash
        self.load()

    @property
    def fingerprints(self):
        """Return key fingerprints

        """
        return [key.fingerprint(self.fingerprint_hash) for key in self]

    def load(self):
        """
        Load authorized keys file, discarding earlier data in the object.

        SSH v1 authorized_keys line: options, bits, exponent, modulus, comment)
        SSH v2 authorized_keys line: options, keytype, base64-encoded key, comment)'

        See man sshd for details.
        """
        del self[0:len(self)]

        if not os.path.isfile(self.path):
            self.log.debug('No such file: {}'.format(self.path))
            return

        for line in [l.rstrip() for l in open(self.path, 'r').readlines()]:
            if line.startswith('#') or line.strip() == '':
                continue

            try:
                self.append(OpenSSHPublicKey(line))
            except SSHKeyError:
                pass


class SSHConfigHostPattern(dict):
    """
    Host entry pattern in SSH configuration
    """
    def __init__(self, config, patterns):
        self.config = config
        self.patterns = patterns.split(' ')

    def __repr__(self):
        return 'Host {}'.format(' '.join(self.patterns))

    def parse(self, line):
        try:
            key, value = [x.strip() for x in line.split(None, 1)]
            if key in ('Compression',  'ForwardAgent',  'ForwardX11',  'TCPKeepAlive'):
                value = value == 'yes' and True or False

            if key in ('ServerAliveInterval', ):
                value = int(value)

            self[key] = value

        except ValueError:
            raise ValueError('Invalid line: {}'.format(line))

    def __getattr__(self, attr):
        if attr in self.keys():
            return self[attr]

        raise AttributeError

    def __getitem__(self, item):
        if item in super(SSHConfigHostPattern, self).keys():
            return super(SSHConfigHostPattern, self).__getitem__(item)
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
        return sorted(list(super(SSHConfigHostPattern, self).keys()) + list(self.config.defaults.keys()))

    def items(self):
        items = []
        for key in self.keys():
            if key in super(SSHConfigHostPattern, self).keys():
                items.append((key, self[key]))
            else:
                items.append((key, self.config.defaults[key]))

        return items

    def values(self):
        items = []
        for key in self.keys():
            if key in super(SSHConfigHostPattern, self).keys():
                items.append(self[key])
            else:
                items.append(self.config.defaults[key])

        return items


class SSHConfig(dict):
    def __init__(self, path=None):
        self.defaults = {}
        self.patterns = []
        self.log = Logger().default_stream
        self.path = path is not None and path or os.path.expanduser('~/.ssh/config')
        self.reload()

    def reload(self):
        self.clear()
        if not os.path.isfile(self.path):
            self.log.debug('No such file: {}'.format(self.path))
            return

        with open(self.path, 'r') as fd:
            host = None
            for line in [x.strip() for x in fd.readlines()]:
                if line == '' or line.startswith('#'):
                    continue

                if line[:5] == 'Host ':
                    host = SSHConfigHostPattern(self, line[5:])
                    for pattern in host.patterns:
                        self[pattern] = host
                    self.patterns.append(host)

                else:
                    host.parse(line)

        if '*' in self.keys():
            self.defaults.update(self.pop('*').items())

    def keys(self):
        return [k for k in sorted(super(SSHConfig, self).keys())]

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def values(self):
        return [self[k] for k in self.keys()]
