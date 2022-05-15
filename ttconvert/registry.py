#!/usr/bin/env python

# converter registry

__author__ = 'Jan Feitsma'


import os


class FolderHandler():
    def __init__(self, handler, arg=None):
        self.handler = handler
        self.desc = str(handler)
        if arg:
            if isinstance(arg, str):
                self.desc = 'pattern ' + arg
                self.pruner = lambda folder: arg in os.path.basename(folder)
            else:
                self.pruner = arg
    def __repr__(self):
        return self.desc

class FileHandler():
    def __init__(self, handler, mask):
        self.handler = handler
        self.mask = mask
    def __repr__(self):
        return 'mask ' + self.mask

class Registry():
    def __init__(self):
        self.folder_handlers = []
        self.file_handlers = []
    def __repr__(self):
        result = 'Registry:\n'
        for fh in self.folder_handlers:
            result += '   folder {}\n'.format(fh)
        for fh in self.file_handlers:
            result += '   file {}\n'.format(fh)
        return result
_registry = Registry()

def get():
    """Get a handle to the registry."""
    return _registry

def add_folder(handler, pruner=None):
    """Register folder handler. The prune option is needed to disambiguate."""
    _registry.folder_handlers.append(FolderHandler(handler, pruner))

def add_file(handler, mask):
    """Register file handler."""
    _registry.file_handlers.append(FileHandler(handler, mask))

