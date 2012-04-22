#!/usr/bin/env python
"""
Password configuration module for LDAP servers

Example password configuration file contents:

[default]
server = ldap://localhost/
admin_dn = cn=manager,dc=example,dc=com
uid_format = uid=%(username)s,%(dn)s

[mail]
description = Mail account password
dn = ou=users,dc=mail,dc=example,dc=com

[shell]
description = Shell access password
dn = ou=users,dc=shell,dc=example,dc=com

"""

#noinspection PyUnresolvedReferences
import os,configobj,string,random,base64,ldap
from hashlib import sha1

DEFAULT_PASSWORD_CONFIG = '/etc/password-services.conf'
VALID_CONFIG_FIELDS = ['server','dn','admin_dn','uid_format','description']
SEARCH_FIELDS = ['uid','gecos']

class PasswordServiceError(Exception):
    """
    Exception raised by issues with LDAP server or password changes
    """
    def __str__(self):
        return self.args[0]

class PasswordServiceConfig(dict):
    """
    Parser for configuration file of LDAP password servers,
    DN and ADMIN DN values.
    """
    def __init__(self,path=None):
        dict.__init__(self)
        path = path is not None and path or DEFAULT_PASSWORD_CONFIG
        self.__admin_credentials_cache = {}
        self.defaults = {
            'server': 'ldap://localhost/',
            'uid_format': 'uid=%(username)s,%(dn)s',
            'dn': None, 'admin_dn': None,
        }
        if not os.path.isfile(path):
            raise PasswordServiceError(
                'No such file: %s' % path
            )
        if not os.access(path,os.R_OK):
            raise PasswordServiceError(
                'No permissions to read %s' % path
            )
        config = configobj.ConfigObj(path,list_values=False,interpolation=False)
        for name,settings in config.items():
            fields = {}
            for k,v in settings.items():
                if k not in VALID_CONFIG_FIELDS:
                    raise PasswordServiceError(
                        'Unknown key in configuration: %s' % k
                    )
                v = unicode(v,'utf-8')
                if name == 'default':
                    self.defaults[k] = v
                else:
                    fields[k] = v
            if name == 'default':
                continue

            for k in ['server','dn','admin_dn','uid_format']:
                if not fields.has_key(k):
                    fields[k] = self.defaults[k]
            self[name] = PasswordService(name,**fields)

    def get_cached_admin_password(self,server):
        """
        Return cached admin DN password or None if not found
        """
        try:
            return self.__admin_credentials_cache[server]
        except KeyError:
            return None

    def cache_admin_password(self,server,password):
        """
        Stores admin DN password to local cache to be used when 
        multiple operatins are requested on same server.
        Always remember to wipe cache with clear_password_cache()
        """
        if self.__admin_credentials_cache.has_key(server):
            # Wipe old value before updating
            for i in enumerate(self.__admin_credentials_cache[server]):
                self.__admin_credentials_cache[server][i] = ''
        self.__admin_credentials_cache[server] = password

    def clear_password_cache(self):
        """
        Clear local admin password cache, overwriting fields with
        empty values before deallocating
        """
        for k,v in self.__admin_credentials_cache.items():
            for i in enumerate(v):
                self.__admin_credentials_cache[k][i] = ''
        self.clear()

class PasswordService(object):
    """
    Stores password service configuration entries from
    PasswordServiceConfig file
    """
    def __init__(self,name,server,dn,admin_dn,uid_format,description=None):
        self.name = name
        self.server = server
        self.uid_format = uid_format
        self.dn = dn
        self.admin_dn = admin_dn
        if description is None:
            description = '%s password' % self.name
        self.description = description

    def __repr__(self):
        return '%s on %s DN %s' % (self.name,self.server,self.dn) 

    def generate_salt(self,chars=None,length=16):
        """
        Generate a random salt. Default length is 16.
        """
        chars = chars is not None and chars or string.letters + string.digits
        salt = ""
        for i in range(int(length)):
            salt += random.choice(chars)
        return salt

    def format_uid(self,username):
        """
        Return UID for username
        """
        return self.uid_format % {'username': username,'dn': self.dn} 

    def test_password(self,username,password,admin=False):
        """
        Test login with the password given
        """
        uid = self.format_uid(username)
        session = ldap.initialize(self.server)
        try:
            if admin:
                session.simple_bind_s(self.admin_dn,password)
            else:
                session.simple_bind_s(uid,password)
        except ldap.UNWILLING_TO_PERFORM:
            return None
        except ldap.INVALID_CREDENTIALS:
            return None
        return session

    def change_password(self,username,new,bind_password,admin=False):
        """
        Change user's password to 'new' for username 'username' 
        If admin is False, we try to bind with user credentials,
        otherwise bind_password is admin_dn password.
        """
        if admin:
            session = self.test_password(username,bind_password,admin=True)
        else:
            session = self.test_password(username,bind_password)
        if not session:
            raise PasswordServiceError('Invalid password')

        # Make sure user exists in LDAP
        uid = self.format_uid(username)
        try:
            info = session.search_s(
                self.dn,ldap.SCOPE_SUBTREE,'(uid=%s)' % username,SEARCH_FIELDS
            )[0]
            #noinspection PyStatementEffect
            info[1]['uid'][0]
        except ldap.FILTER_ERROR,emsg:
            raise PasswordServiceError('Error in query: %s' % emsg)
        except IndexError:
            raise PasswordServiceError('User not found from LDAP')

        salt = self.generate_salt()
        # TODO - make this configurable
        pwhash = "{SSHA}" + base64.encodestring(sha1(new+salt).digest() + salt)
        mod_attrs = [ ( ldap.MOD_REPLACE, 'userPassword', pwhash ) ]
        try:
            session.modify_s(uid,mod_attrs)
        except ldap.INVALID_CREDENTIALS,emsg:
            # TODO - check what exceptions actually can be raised here
            raise PasswordServiceError(
                'Error changing password for %s: %s' % (uid,emsg)
            )

