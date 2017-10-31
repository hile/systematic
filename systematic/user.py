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


class User(object):
    """
    User from pwd api
    """
    def __init__(self, db, pwent):
        self.db = db
        self.name = pwent.pw_name
        self.gecos = pwent.pw_gecos
        self.uid = pwent.pw_uid
        self.gid = pwent.pw_gid
        self.shell = pwent.pw_shell
        self.directory = pwent.pw_dir

    @property
    def group(self):
        return self.db.lookup_gid(self.gid)

    def __repr__(self):
        return '{0} {1}'.format(self.__class__, self.name)


class Group(object):
    """
    Group from grp api
    """
    def __init__(self, db, gr_ent):
        self.db = db
        self.name = gr_ent.gr_name
        gid = gr_ent.gr_gid
        self.member_uids = gr_ent.gr_mem

    def __repr__(self):
        return '{0} {1}'.format(self.__class__, self.name)


class UnixPasswordDB(object):
    """
    Wrap pwd and grp to objects
    """

    def __init__(self, cache_seconds=DEFAULT_CACHE_SECONDS):
        self.cache_seconds = cache_seconds
        self.users = OrderedDict()
        self.groups = OrderedDict()

        self.__groups_updated__ = None
        self.__users_updated__ = None

    def load_groups(self):
        """Load group details

        Loads all group entries from pwd. On a large system this may be
        very slow.
        """
        if self.__groups_updated__ is None or (time.time() - self.__groups_updated__) > self.cache_seconds:
            self.groups = OrderedDict()
            for grent in sorted(grp.getgrall(), key=attrgetter('gr_gid')):
                self.groups[grent.gr_gid] = (Group(self, grent))
            self.__groups_updated__ = time.time()
        return self.groups

    def load_users(self):
        """Load user details

        Loads all user entries from pwd. On a large system this may be
        very slow.
        """
        if self.__users_updated__ is None or (time.time() - self.__users_updated__) > self.cache_seconds:
            self.users = OrderedDict()
            for pwent in sorted(pwd.getpwall(), key=attrgetter('pw_uid')):
                self.users[pwent.pw_uid] = (User(self, pwent))
            self.__users_updated__ = None
        return self.users

    def lookup_gid(self, gid):
        """Get group

        Get a single group by gid, storing it to self.groups as well
        """
        if gid not in self.groups:
            try:
                self.groups[gid] = Group(self, grp.getgrgid(gid))
            except:
                raise ValueError('Group with GID {0} not found'.format(gid))
        return self.groups[gid]

    def lookup_uid(self, uid):
        """Get group

        Get a single group by gid, storing it to self.groups as well
        """
        if uid not in self.users:
            try:
                self.users[uid] = User(self, pwd.getpwuid(uid))
            except Exception as e:
                print e
                raise ValueError('User with UID {0} not found'.format(uid))
        return self.users[uid]
