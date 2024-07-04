# -*- coding: utf-8 -*-


import os
from glob import glob, escape
from operator import attrgetter
from tempfile import mkdtemp, mkstemp
from os.path import abspath, basename, dirname, exists, expanduser, isabs, isdir, join, normpath, splitext

from compress import check_compressed_vfs, get_compressed_file_engine
from utils import copy_bulk, delete_bulk, get_filetype, overwrite_vfsfile, \
                  ProcessCommand, run_in_cli, text2wrap, size2str, time2str, \
                  perms2str, owner2str, group2str, type2str, rdev2str
from common import *


########################################################################
##### FS Configuration
class FSConfig:
    def __init__(self):
        self.filters = ''
        self.show_dotfiles = True
        self.sort_type = SortType.byName
        self.sort_reverse = False
        self.sort_mix_dirs = False
        self.sort_mix_cases = True

    def fill_with_app(self, cfg):
        self.show_dotfiles = cfg.options.show_dotfiles
        self.sort_type = cfg.options.sort_type
        self.sort_reverse = cfg.options.sort_reverse
        self.sort_mix_dirs = cfg.options.sort_mix_dirs
        self.sort_mix_cases = cfg.options.sort_mix_cases

    def get_sort_key(self):
        if self.sort_type == SortType.none:
            return lambda x: 0
        elif self.sort_type == SortType.byName:
            return lambda x: (attrgetter('name')(x).lower() if self.sort_mix_cases else attrgetter('name')(x))
        elif self.sort_type == SortType.byExt:
            return lambda x: (attrgetter('ext')(x).lower() if self.sort_mix_cases else attrgetter('ext')(x))
        elif self.sort_type == SortType.byPath:
            return lambda x: (attrgetter('path_str')(x).lower() if self.sort_mix_cases else attrgetter('path_str')(x))
        elif self.sort_type == SortType.bySize:
            return attrgetter('size')
        elif self.sort_type == SortType.byMTime:
            return attrgetter('mtime')
        else:
            raise KeyError


########################################################################
##### FSEntry
class FSEntry:
    """File System entry"""

    def __init__(self, pfile):
        self.pfile = pfile
        self.pdir = dirname(pfile)
        self.name = basename(pfile)
        self.name_noext, self.ext = splitext(self.name)
        if self.name_noext.endswith('.tar'):
            self.name_noext = self.name_noext.replace('.tar', '')
            # self.ext = '.tar' + self.ext
        st = os.lstat(pfile)
        self.size = st.st_size
        self.mode = st.st_mode
        self.owner = st.st_uid
        self.group = st.st_gid
        self.mtime = st.st_mtime
        self.stat = st
        self.type = get_filetype(pfile)
        if self.type in (FileType.cdev, FileType.bdev):
            try:
                r = st.st_rdev
                self.rdev = r >> 8, r & 255
            except AttributeError:
                self.rdev = 0, 0
        else:
            self.rdev = 0, 0
        # string representation of attributes
        self.path_str = str(pfile)
        self.size_str = size2str(self.size)
        self.mtime_str = time2str(self.mtime)
        self.mtime2_str = time2str(self.mtime, short=False)
        self.mode_str = perms2str(self.mode)
        self.owner_str = owner2str(self.owner)
        self.group_str = group2str(self.group)
        self.type_str = type2str(self.type)
        self.rdev_str = rdev2str(self.rdev)

    def format(self, fields, sep='|'):
        # fields is a list of tuples [('attribute', length)]
        #   ls = ['{0.%s:%ds}' % (attr, length) for attr, length in fields]
        #   fmt = sep.join(ls)
        #   return fmt.format(self)
        ls = []
        for attr, length in fields:
            ljust = True
            if attr in ('size', ):
                if self.type in (FileType.cdev, FileType.bdev):
                    attr, length = 'rdev_str', 7
                else:
                    attr, ljust = 'size_str', False
            elif attr in ('mtime', 'mtime2', 'mode', 'owner', 'group', 'type'):
                attr += '_str'
            txt = sep*length if attr=='sep' else text2wrap(getattr(self, attr), length, ljust)
            ls.append(txt)
        return ''.join(ls)

    def __repr__(self):
        return '<FSEntry: {}>'.format(self.name)

    def get_type_from_ext(self, files_ext):
        if self.is_dir:
            return 'dir'
        elif self.type == FileType.exe:
            return 'exe'
        else:
            for ftype in files_ext.keys():
                if self.ext[1:] in files_ext[ftype]:
                    return ftype
            else:
                return 'reg'

    @property
    def is_dir(self):
        return self.type in (FileType.dir, FileType.link2dir)

    @property
    def is_link(self):
        return self.type in (FileType.link2dir, FileType.link, FileType.nlink)

    @property
    def is_dotfile(self):
        return self.name[0] == '.'

    def is_filtered(self, fs_hide, fs_show):
        """Returns if a file should be filtered (hidden) or not.
        Accepts 2 lists: first items to hide, second items to show.
        If a file is in both lists, it is shown"""
        if len(fs_show)==0 and len(fs_hide)==0:
            return False
        return False if self.pfile in fs_show else self.pfile in fs_hide

    def update_size(self, size):
        self.size = size
        self.size_str = size2str(size)


########################################################################
##### BaseFolder
class BaseFolder:
    """Base Folder"""

    def __init__(self, base, rel='', parfs=None):
        self.parfs = parfs
        self.cfg = FSConfig()
        adir = expanduser(base if VFS_STRING in base else normpath(base))
        if not isabs(adir):
            adir = abspath(adir)
        if rel != '':
            rel = normpath(rel)
        self.prepare_paths(adir, rel)
        self.pre_init()
        self.load()

    def __len__(self):
        return len(self._items_sorted)

    def __getitem__(self, key):
        return self._items_sorted.__getitem__(key)

    def __repr__(self):
        if self.vfs:
            return '<{}: {} [{}]>'.format(self.clsname, self.path_str, self.pdir)
        else:
            return '<{}: {}>'.format(self.clsname, self.path_str)

    def dump_info(self):
        log.info('##### {}'.format(self))
        log.info('##### base:  {} {}'.format(self.base, self.rel))
        log.info('##### rbase: {} {}'.format(self.rbase, self.rel))
        log.info('##### pdir:  {}'.format(self.pdir))
        log.info('##### parfs: {}'.format(self.parfs))

    @property
    def nfiltered(self):
        return len(self._items) - len(self._items_sorted) + 1 # pardir

    @property
    def path_str(self):
        return self.base + self.rel

    @property
    def base_filename(self):
        return self.base[:-len(VFS_STRING)] if self.base.endswith(VFS_STRING) else self.base

    @property
    def dirname(self):
        if self.path_str.endswith(VFS_STRING):
            if self.clsname == 'CompressedFileFolder':
                # root of vfsfile (compressedfile) -> dir of vfsfile
                parent = dirname(self.path_str[:-len(VFS_STRING)])
            else:
                # root of vfsfile (search) -> vfsfile
                parent = self.path_str[:-len(VFS_STRING)]
        else:
            parent = dirname(self.path_str)
            if parent.endswith('#vfs:'):
                parent += '//'
        return parent

    @property
    def basename(self):
        return basename(self.path_str[:-len(VFS_STRING)] if self.path_str.endswith(VFS_STRING) else self.path_str)

    def prepare_paths(adir, rel):
        """Method called to initiale paths.
        'adir' is str, 'rel' is str"""
        raise NotImplementedError

    def pre_init(self):
        """Method called after initializing paths but before load contents"""
        raise NotImplementedError

    def exit(self, all_levels=False, rebuild=False):
        """Method to be called at folder destruction"""
        raise NotImplementedError

    def chdir(self, rel):
        """Method called before changing directory"""
        raise NotImplementedError

    def load(self):
        """Load folder contents. Call when path contents have change"""
        log.debug('Load {} [{}]'.format(self, self.pdir))
        self._items = [FSEntry(join(self.pdir, f)) for f in os.listdir(self.pdir)]

    def refresh(self):
        """Apply filters and sort entries. Call when config, sorting or filters change"""
        log.debug('Refresh {} [{}]'.format(self, self.pdir))
        ds, fs = list(), list()
        if self.cfg.filters == '':
            fs_hide, fs_show = self.get_filtered('!.*,!*') # show all
        else:
            fs_hide, fs_show = self.get_filtered(self.cfg.filters)
        if self.cfg.sort_mix_dirs:
            fs = [it for it in self._items if (self.cfg.show_dotfiles and it.is_dotfile or not it.is_dotfile)
                                              and (not it.is_filtered(fs_hide, fs_show))]
        else:
            for it in self._items:
                if not self.cfg.show_dotfiles and it.is_dotfile:
                    continue
                if it.is_filtered(fs_hide, fs_show):
                    continue
                if it.is_dir:
                    ds.append(it)
                else:
                    fs.append(it)
        key = self.cfg.get_sort_key()
        ds.sort(key=key, reverse=self.cfg.sort_reverse)
        ds.insert(0, FSEntry(join(self.pdir, '..'))) # insert parent dir
        fs.sort(key=key, reverse=self.cfg.sort_reverse)
        ds.extend(fs)
        self._items_sorted = ds

    def lookup(self, filename):
        """Returns FSEntry if file exists in directory"""
        for f in self._items_sorted:
            if f.name == filename:
                return f
        else:
            return None

    def pos(self, filename):
        """Returns the position index if file exists in directory"""
        for f in self._items_sorted:
            if f.name == filename:
                return self._items_sorted.index(f)
        else:
            return -1

    def get_filenames(self, start=0):
        """Returns a (sub)list with the sorted dirs/files names in directory"""
        return [f.name for f in self._items_sorted[start:]]

    def get_filtered(self, filters):
        """Returns entries that match any of the globs.
        If glob starts with ! add match to 2nd list"""
        globs = [] if filters=='' else [f.strip() for f in filters.split(',')]
        fs_hide, fs_show = [], []
        p = escape(self.pdir)
        for g in globs:
            if g.startswith('!'):
                fs_show.extend(glob(join(p, g[1:])))
            else:
                fs_hide.extend(glob(join(p, g)))
        return fs_hide, fs_show

    @property
    def dirs(self):
        return [it for it in self._items_sorted if it.is_dir and it.name!=os.pardir]


########################################################################
##### LocalFolder
class LocalFolder(BaseFolder):
    """Local File System Folder"""

    clsname = 'LocalFolder'

    def prepare_paths(self, adir, _):
        assert isdir(adir)
        self.base = self.rbase = ''
        self.pdir = self.rel = adir
        self.vfs = False
        self.vfs_str = ''

    def pre_init(self):
        pass

    def exit(self, all_levels=False, rebuild=False):
        pass

    def chdir(self, rel):
        raise RuntimeError


########################################################################
##### CompressedFileFolder
class CompressedFileFolder(BaseFolder):
    """Compressed File Folder"""

    clsname = 'CompressedFileFolder'

    def prepare_paths(self, adir, rel):
        self.base = adir + VFS_STRING
        self.rbase = mkdtemp(suffix='.lfm')
        self.rel = rel
        self.pdir = join(self.rbase, rel)
        self.vfs = True
        self.vfs_str = VFS_STRING
        self.already_exited = False

    def pre_init(self):
        log.debug('Preparing VFS: {}'.format(self))
        c = get_compressed_file_engine(self.base.replace(VFS_STRING, ''))
        if c is None:
            raise
        st, res, err = ProcessCommand('Creating VFS', self.base_filename,
                                      c.cmd_uncompress, path=self.rbase).run()
        if st == -100: # stopped by user
            delete_bulk(self.rbase, ignore_errors=True)
            raise UserWarning('Stopped by user')
        if err != '':
            delete_bulk(self.rbase, ignore_errors=True)
            raise UserWarning(err)

    def exit(self, all_levels=False, rebuild=False):
        if self.already_exited:
            return
        log.debug('Exiting from VFS: {}'.format(self))
        if all_levels:
            parfs = self.parfs
            while parfs:
                parfs.exit()
                parfs = parfs.parfs
        if rebuild:
            self.__rebuild()
        delete_bulk(self.rbase, ignore_errors=True)
        self.already_exited = True

    def chdir(self, rel):
        self.rel = rel
        new_pdir = join(self.rbase, rel)
        if isdir(new_pdir):
            self.pdir = new_pdir
            log.debug('VFS: chdir {} -> {}'.format(self, self.pdir))
            self.load()
            return self
        else:
            log.debug('VFS in VFS: {} -> {}'.format(self, self.pdir))
            log.debug('New folder: path="{}", oldfs={}'.format(new_pdir, '"%s"' % self))
            base, rel = split_vfs_path(new_pdir)
            newfs = open_folder(base, rel, self, True)
            newfs.base = self.path_str + VFS_STRING
            return newfs

    def __rebuild(self):
        log.debug('Rebuilding VFS: {}'.format(self))
        c = get_compressed_file_engine(self.base.replace(VFS_STRING, ''))
        if c is None:
            raise
        _, tmpfile = mkstemp(suffix='.lfm')
        st, res, err = ProcessCommand('Rebuilding VFS', self.base_filename,
                                      c.cmd_compress2('*', tmpfile), path=self.rbase).run()
        # compress process always create filename with extension
        delete_bulk(tmpfile, ignore_errors=True)
        tmpfile_ext = tmpfile + c.exts[0]
        if st == -100: # stopped by user
            delete_bulk(tmpfile_ext, ignore_errors=True)
            delete_bulk(self.rbase, ignore_errors=True)
            raise UserWarning('Stopped by user')
        if err != '':
            delete_bulk(tmpfile_ext, ignore_errors=True)
            delete_bulk(self.rbase, ignore_errors=True)
            raise UserWarning(err)
        try:
            overwrite_vfsfile(tmpfile_ext, c.path)
        except OSError as err:
            delete_bulk(tmpfile_ext, ignore_errors=True)
            raise


########################################################################
##### SearchFolder
class SearchFolder(BaseFolder):
    """Search Folder"""

    clsname = 'SearchFolder'

    def prepare_paths(self, adir, rel):
        self.base = adir + VFS_STRING
        self.rbase = mkdtemp(suffix='.lfm')
        self.rel = rel
        self.pdir = join(self.rbase, rel)
        self.vfs = True
        self.vfs_str = VFS_STRING

    def pre_init(self):
        pass

    def copy_files(self, files):
        log.debug('Preparing VFS: {}'.format(self))
        self.files = files
        for f in files:
            src = join(self.parfs.pdir, f)
            dest = join(self.pdir, f)
            os.makedirs(dirname(dest), exist_ok=True)
            copy_bulk(src, dest)
        self.load()
        return self

    def exit(self, all_levels=False, rebuild=False):
        log.debug('Exiting from VFS: {}'.format(self))
        if rebuild:
            self.__rebuild()
        delete_bulk(self.rbase, ignore_errors=True)

    def chdir(self, rel):
        self.rel = rel
        self.pdir = join(self.rbase, rel)
        log.debug('Search VFS: chdir {} -> {}'.format(self, self.pdir))
        self.load()
        return self

    def __rebuild(self):
        log.debug('Rebuilding VFS: {}'.format(self))
        files = [f[2:] for f in run_in_cli('find . -type f', self.pdir)[0].split()]
        deleted = set(self.files) - set(files)
        for f in files:
            src = join(self.pdir, f)
            dest = join(self.parfs.pdir, f)
            os.makedirs(dirname(dest), exist_ok=True)
            copy_bulk(src, dest)
        for f in deleted:
            dest = join(self.parfs.pdir, f)
            delete_bulk(dest, ignore_errors=True)


########################################################################
def split_vfs_path(path):
    n = path.rfind(VFS_STRING) # can be vfs in vfs => rfind, not find!
    if n == -1:
        base, rel = path, ''
    else:
        base, rel = path[:n+len(VFS_STRING)], path[n+len(VFS_STRING):]
    return base, rel

def open_folder(base, rel, oldfs, vfsinvfs):
    if isdir(base):
        if rel != '':
            raise ValueError
        return LocalFolder(base)
    if base.endswith(VFS_STRING):
        base = base[:-len(VFS_STRING)]
    if check_compressed_vfs(base):
        if not vfsinvfs and oldfs and oldfs.parfs and exists(oldfs.parfs.pdir):
            oldfs.parfs.rel = dirname(oldfs.parfs.rel)
            return oldfs.parfs
        else:
            return CompressedFileFolder(base, rel, oldfs)
    raise FileNotFoundError

def is_delete_oldfs(newpath, oldfs):
    """Returns if we will exit oldfs in next new_folder()"""
    base, rel = split_vfs_path(newpath)
    return oldfs and oldfs.vfs and base!=oldfs.base and not basename(newpath)==basename(oldfs.path_str)

def new_folder(path, oldfs=None, rebuild_if_exit=False, files=None):
    # path is str, oldfs is BaseFolder!
    if files:
        log.debug('New searchvfs folder: path="{}", oldfs={}'.format(path, '"%s"' % oldfs if oldfs else 'none'))
        return SearchFolder(path, parfs=oldfs).copy_files(files)
    log.debug('New folder: path="{}", oldfs={}'.format(path, '"%s"' % oldfs if oldfs else 'none'))
    base, rel = split_vfs_path(path)
    if not oldfs:
        return open_folder(base, rel, None, False)
    if base == oldfs.base:
        return oldfs.chdir(rel)
    else:
        if basename(path) != basename(oldfs.path_str) or path.endswith(VFS_STRING) \
           and oldfs.path_str.endswith(VFS_STRING+VFS_STRING): # exit vfs
            oldfs.exit(rebuild=rebuild_if_exit)
            if oldfs.clsname == 'SearchFolder':
                return oldfs.parfs
        return open_folder(base, rel, oldfs, False)


########################################################################
