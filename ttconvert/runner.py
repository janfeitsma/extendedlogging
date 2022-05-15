#!/usr/bin/env python

# conversion runners

__author__ = 'Jan Feitsma'


import os
import shutil
import time
from fnmatch import fnmatch
import ttconvert.registry as registry



class Runner():
    def __init__(self, tmpdir, inputfiles, outputhtmlfile, sizelimit_mb):
        self.tmpdir = tmpdir
        self.inputfiles = inputfiles
        self.outputhtmlfile = outputhtmlfile
        self.sizelimit_mb = sizelimit_mb
        self.messager = lambda x: None
        self.dryrun = False
        self.registry = registry.get()
        self.jsons = []

    def run(self):
        """Given one or more input files, or a single folder - produce a html file."""
        n = len(self.inputfiles)
        if n == 0:
            raise Exception('expected one or more files, or a single folder')    
        elif n == 1 and os.path.isdir(self.inputfiles[0]):
            self.run_dir(self.inputfiles[0])
        else:
            self.run_files(self.inputfiles)
        jsonfile = self.merge() # merge is skipped in case of 1 json file
        self.convert(jsonfile, os.path.join(self.tmpdir, 'ttviewer.html'))

    def run_dir(self, inputdir):
        """Run on a directory."""
        if len(self.registry.folder_handlers) == 0:
            raise Exception('no folder handlers found in registry')
        handle = None
        if len(self.registry.folder_handlers) == 1:
            handle = self.registry.folder_handlers[0].handle
        else:
            handle = self._get_folder_handler(inputdir)
        # run
        handle(self, inputdir)

    def run_files(self, inputfiles):
        """Run on a set of files."""
        # type check
        for f in inputfiles:
            assert os.path.isfile(f), 'cannot mix files with folder: ' + f
        # size check
        for f in inputfiles:
            if os.path.getsize(f) / 1024.0**2 > self.sizelimit_mb:
                raise Exception('input file size ({}) of {} exceeds limit of {:.1f}MB'.format(f, self._filesize(f), self.sizelimit_mb))
        # run
        for f in inputfiles:
            if f.endswith('.json'):
                self.copy(f)
            else:
                self.convert(f)

    def copy(self, f):
        """Copy given json to tmpdir."""
        tgt = os.path.join(self.tmpdir, os.path.basename(f))
        self.jsons.append(tgt)
        # message
        begin_message = 'Copying'
        if self.dryrun:
            begin_message = 'dryrun: Copy'
        self.messager('{} {} to {}'.format(begin_message, f, self.tmpdir))
        # copy
        shutil.copy(f, self.tmpdir)

    def convert(self, srcfile, tgtfile=None):
        """Convert a single file."""
        # get converter
        converter = self._get_file_handler(srcfile)
        # determine target file and register it
        if tgtfile is None:
            tgtfile = os.path.join(self.tmpdir, os.path.basename(srcfile) + '.json')
        self.jsons.append(tgtfile)
        # message
        begin_message = 'Converting'
        if self.dryrun:
            begin_message = 'dryrun: Convert'
        def describe_converter(converter):
            if hasattr(converter, 'tool'):
                return 'tool: ' + os.path.basename(converter.tool)
            if hasattr(converter, 'parser'):
                return 'parser: ' + type(converter.parser).__name__
            # just show function name
            return converter.__name__
        self.messager('{} {} ({}) to {} using {} ...'.format(begin_message, srcfile, self._filesize(srcfile), tgtfile, describe_converter(converter)), newline=self.dryrun)
        # stop in case of dryrun
        if self.dryrun:
            return
        # do the conversion
        t_start = time.time()
        n = converter(srcfile, tgtfile)
        elapsed = time.time() - t_start
        details = '{:.1f}s, {}'.format(elapsed, self._filesize(tgtfile))
        if n:
            details += ', n={}'.format(n)
        self.messager(' done ({})\n'.format(details))

    def merge(self):
        """Merge all jsons in tmpdir."""
        # no merge needed if there is only a single json file
        if len(self.jsons) <= 1:
            return self.jsons[0]
        # merge is needed
        tgtfile = os.path.join(self.tmpdir, 'merged.json')
        # message
        begin_message = 'Merging'
        if self.dryrun:
            begin_message = 'dryrun: Merge'
        self.messager('{} {} .json files into {} ...'.format(begin_message, len(self.jsons), tgtfile, newline=self.dryrun))
        # stop in case of dryrun
        if self.dryrun:
            return
        # do the merge
        raise NotImplementedError('json merge')

    # helpers / internals below         

    @staticmethod
    def _filesize(filename):
        if not os.path.isfile(filename):
            return '<unknown size>'
        numbytes = os.path.getsize(filename)
        if os.path.getsize(filename) < 1000:
            return '{:d}B'.format(numbytes)
        elif os.path.getsize(filename) < 1e6:
            return '{:.1f}KB'.format(numbytes / 1024.0)
        elif os.path.getsize(filename) < 1e9:
            return '{:.1f}MB'.format(numbytes / 1024.0**2)
        return '{:.1f}GB'.format(numbytes / 1024.0**3)

    def _get_file_handler(self, f):
        bb = [fnmatch(f, fh.mask) for fh in self.registry.file_handlers]
        if sum(bb) == 0:
            raise Exception('none of the registered file masks apply to {}\n{}'.format(f, self.registry))
        if sum(bb) > 1:
            raise Exception('multiple file masks apply\n{}'.format(self.registry))
        return self.registry.file_handlers[bb.index(True)].handler

    def _get_folder_handler(self, inputdir):
        # select by pruning
        bb = [fh.pruner(inputdir.rstrip('/')) for fh in self.registry.folder_handlers]
        if sum(bb) == 0:
            raise Exception('none of the folder handlers accepts this folder\n{}'.format(self.registry))
        if sum(bb) > 1:
            raise Exception('multiple of the folder handlers accept this folder, use prune functions and/or rename to disambiguate\n{}'.format(self.registry))
        return self.registry.folder_handlers[bb.index(True)].handler

