"""
Caching and object based wrapper for pwd/grp system calls
"""

import grp
import os
import pwd
import time

from collections import OrderedDict
from operator import attrgetter

# How long to cache the user and group details
DEFAULT_CACHE_SECONDS = 300


class DatabaseError(Exception):
    pass


class User(object):
    """
    User from pwd api
    """
    idattr = 'uid'
    nameattr = 'username'

    def __init__(self, db, pwent):
        self.db = db
        self.username = pwent.pw_name
        self.password = pwent.pw_passwd
        self.gecos = pwent.pw_gecos
        self.uid = pwent.pw_uid
        self.gid = pwent.pw_gid
        self.shell = pwent.pw_shell
        self.directory = pwent.pw_dir

    def __repr__(self):
        return '{0} {1}'.format(self.__class__, self.username)

    @property
    def group(self):
        return self.db.groups.lookup_id(self.gid)


class Group(object):
    """
    Group from grp api
    """
    idattr = 'gid'
    nameattr = 'name'

    def __init__(self, db, gr_ent):
        self.db = db
        self.gid = gr_ent.gr_gid
        self.password = gr_ent.gr_passwd
        self.name = gr_ent.gr_name
        self.member_uids = gr_ent.gr_mem

    def __repr__(self):
        return '{0} {1}'.format(self.__class__, self.name)

    def validate_members(self):
        """Validate members

        Raise DatabaseError with member usernames not found from user database
        """
        self.db.load()
        notfound = []
        for name in self.member_uids:
            try:
                self.db.users.lookup_name(name)
            except DatabaseError:
                notfound.append(name)
        if notfound:
            raise DatabaseError('Error looking up users: {0}'.format(
                ' '.join(notfound)
            ))

    @property
    def members(self):
        """Return users for group

        Note: only returns existing users. Any username not found is silently ignored
        """
        members = []
        for name in self.member_uids:
            try:
                members.append(self.db.users.lookup_name(name))
            except DatabaseError:
                pass
        return members


class DatabaseEntryMap(object):
    """Entry map

    Maps entry objects by uid/gid and name
    """
    def __init__(self, db, cache_seconds=DEFAULT_CACHE_SECONDS):
        self.db = db
        self.cache_seconds = cache_seconds
        self.__updated__ = None
        self.__id_map__ = {}
        self.__name_map__ = {}

    def __load_entry__(self, entry):
        """Add entry

        """
        self.__id_map__[getattr(entry, entry.idattr)] = entry
        self.__name_map__[getattr(entry, entry.nameattr)] = entry

    @property
    def __is_cached_data_valid__(self):
        """Check if cached data is still valid

        """
        if self.__updated__ is None:
            return False

        try:
            return (time.time() - self.__updated__) <= self.cache_seconds
        except:
            return False

    def lookup_id(self, attr):
        """Lookup entry by gid/uid

        """
        if attr not in self.__id_map__:
            self.__load_by_id__(attr)
        return self.__id_map__[attr]

    def lookup_name(self, name):
        """Lookup entry by gid/uid

        """
        if name not in self.__name_map__:
            self.__load_by_name__(name)
        return self.__name_map__[name]


class UserMap(DatabaseEntryMap):
    """User map

    """
    def load(self):
        """Load password database

        """
        if not self.__is_cached_data_valid__:
            for pwent in sorted(pwd.getpwall(), key=attrgetter('pw_uid')):
                self.__load_entry__(User(self.db, pwent))
            self.__updated__ = time.time()

    def __load_by_id__(self, uid):
        """Load single user by UID

        """
        try:
            self.__load_entry__(User(self.db, pwd.getpwuid(uid)))
        except:
            raise DatabaseError('No such uid: {0}'.format(uid))

    def __load_by_name__(self, name):
        """Load by user name

        """
        try:
            self.__load_entry__(User(self.sb, pwd.getpwnam(name)))
        except:
            raise DatabaseError('No such user: {0}'.format(name))


class GroupMap(DatabaseEntryMap):
    """User map

    """
    def load(self):
        """Load group database

        """
        if not self.__is_cached_data_valid__:
            for grent in sorted(grp.getgrall(), key=attrgetter('gr_gid')):
                self.__load_entry__(Group(self.db, grent))
            self.__updated__ = time.time()

    def __load_by_id__(self, gid):
        """Load group by GID

        """
        try:
            self.__load_entry__(Group(self.db, grp.getgrgid(gid)))
        except:
            raise DatabaseError('No such uid: {0}'.format(gid))

    def __load_by_name__(self, name):
        """Load by group name

        """
        try:
            self.__load_entry__(Group(self.db, grp.getgrnam(name)))
        except:
            raise DatabaseError('No such user: {0}'.format(name))


class UnixPasswordDB(object):
    """
    Wrap pwd and grp to objects
    """

    def __init__(self, cache_seconds=DEFAULT_CACHE_SECONDS):
        self.users = UserMap(self, cache_seconds)
        self.groups = GroupMap(self, cache_seconds)

    def load_groups(self):
        """Load group details

        Loads all group entries from pwd. On a large system this may be
        very slow.
        """
        self.groups.load()

    def load_users(self):
        """Load user details

        Loads all user entries from pwd. On a large system this may be
        very slow.
        """
        self.users.load()

    def load(self):
        """Load both groups and users

        """
        self.load_groups()
        self.load_users()

    def lookup_gid(self, gid):
        """Get group

        Get a single group by gid
        """
        return self.groups.lookup_id(gid)

    def lookup_group(self, name):
        """Get group

        Get a single group by name
        """
        return self.groups.lookup_name(name)

    def lookup_uid(self, uid):
        """Get group

        Get a single group by gid
        """
        return self.users.lookup_id(uid)

    def lookup_user(self, name):
        """Get user

        Get a single user by name
        """
        return self.users.lookup_name(name)

    def get_user_groups(self, username):
        """Return user groups

        Return groups where user is member
        """
        user = self.users.lookup_name(username)
        groups = [ user.group ]
        for gid in self.groups.__id_map__:
            group = self.groups.__id_map__[gid]
            if user.username in group.member_uids:
                groups.append(group)
        return groups
