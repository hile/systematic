#!/usr/bin/env python

import logging,appscript

FOLDER_NAME_MAP = {
    'applications': 'applications_folder',
    'application_support': 'application_support_folder',
    'desktop':  'desktop_folder',
    'desktop_pictures': 'desktop_pictures_folder',
    'documents': 'documents_folder',
    'downloads': 'downloads_folder',
    'favorites': 'favorites_folder',
    'fonts': 'fonts_folder',
    'home': 'home_folder',
    'library': 'library_folder',
    'movies': 'movies_folder',
    'music': 'music_folder',
    'pictures': 'pictures_folder',
    'public': 'public_folder',
    'scripts': 'scripting_additions_folder',
    'shared_documents': 'shared_documents_folder',
    'sites': 'sites_folder',
    'speakable_items': 'speakable_items_folder',
    'temp': 'temporary_items_folder',
    'trash': 'trash',
    'utilities': 'utilities_folder',
    'workflows': 'workflows_folder',
}

class SystemEventsError(Exception):
    def __str__(self):
        return self.args[0]

class OSXUserAccounts(dict):
    def __init__(self):
        try:
            self.app = appscript.app('System Events')
        except appscript.reference.CommandError,e:
            raise SystemEventsError(
                'Appscript initialization error: %s' % e.errormessage
            )
        for ref in self.app.users.get():
            u = OSXUserAccount(self,ref)
            self[u.name] = u

class OSXUserAccount(dict):
    def __init__(self,app,reference):
        self.app = app
        self.reference = reference

    def __getattr__(self,attr):
        try:
            return self[attr]
        except KeyError:
            pass
        raise AttributeError

    def __getitem__(self,item):
        if item not in self.keys():
            raise KeyError('No such OSXUserAccount item: %s' % item)
        if item == 'home_directory':
            return getattr(self.reference,item).get().path
        return getattr(self.reference,item).get()

    def __str__(self):
        return self.full_name

    def keys(self):
        return [k.name for k in self.reference.properties.get().keys()]

    def items(self):
        return [(k,self[k]) for k in self.keys()]

class OSXUserFolders(dict):
    def __init__(self):
        try:
            self.app = appscript.app('System Events')
        except appscript.reference.CommandError,e:
            raise SystemEventsError(
                'Appscript initialization error: %s' % e.errormessage
            )
        for k in sorted(FOLDER_NAME_MAP.keys()):
            ref = getattr(self.app,FOLDER_NAME_MAP[k]).get()
            if ref == None:
                self[k] = None
                continue
            self[k] = OSXFolderItem(self,ref)
            print self[k]

class OSXFolderItem(dict):
    def __init__(self,app,reference):
        if reference is None:
            raise 
        self.app = app
        self.reference = reference

    def __getattr__(self,attr):
        try:
            return self[attr]
        except KeyError:
            pass
        raise AttributeError

    def __getitem__(self,item):
        if item in ['ctime','mtime']:
            if item == 'ctime':
                item = 'creation_date'
            if item == 'mtime':
                item = 'modification_date'
            return int(getattr(self.reference,item).get().strftime('%s'))
        if item == 'path':
            item = 'POSIX_path'
        if item not in self.keys():
            raise KeyError('No such OSXFolderItem item: %s' % item)
        return getattr(self.reference,item).get()

    def __str__(self):
        return self.path

    def keys(self):
        return [k.name for k in self.reference.properties.get().keys()] + [
            'ctime','mtime','path'
        ]

    def items(self):
        return [(k,self[k]) for k in self.keys()]

if __name__ == '__main__':
    import sys
    accounts = OSXUserAccounts()
    for u in accounts.keys():
        print u,accounts[u].items()
    sys.exit(0)
    folders = OSXUserFolders()
    for k in sorted(FOLDER_NAME_MAP.keys()):
        v = folders[k]
        print v.keys()
        for k,v in v.items():
            print k,v
        break
        if v is None:
            continue
        print v.name,v.path,v.mtime

