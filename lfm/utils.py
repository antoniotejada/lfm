#  -*- coding: utf-8 -*-


import os
import sys
import pwd
import grp
import difflib
import stat
import errno
import pkg_resources
from ctypes import CDLL
from datetime import datetime
from collections import OrderedDict
from shutil import copytree, copy2, copystat, move, rmtree
from signal import SIGCONT, SIGKILL, SIGSTOP
from subprocess import check_output, Popen, PIPE, STDOUT
from multiprocessing import Process, Queue, Pipe
from os.path import basename, dirname, exists, expanduser, expandvars, getsize, \
                    isabs, isdir, isfile, islink, join, normpath, relpath
from string import whitespace, punctuation
from time import asctime, localtime, sleep, strftime, time, tzname

from common import *


########################################################################
##### Module variables
use_wide_chars = False


########################################################################
###### LFM
def get_lfm_data_file_contents(filename):
    return str(pkg_resources.resource_string('lfm', 'etc/' + filename), 'UTF-8')


########################################################################
##### Decorators
# Decorator for public callable actions
from functools import wraps
from inspect import getmembers, isfunction

def public(f):
    @wraps(f)
    def wrapper(*a, **k):
        return f(*a, **k)
    setattr(wrapper, 'public', True)
    return wrapper

def get_public_actions():
    import actions
    fns = getmembers(actions, isfunction)
    return [name for name, fn in fns if hasattr(fn, 'public')]

def is_public_api(fn):
    return hasattr(fn, 'public')

# Decorator for catching OSError
def catch_os_exception(f):
    @wraps(f)
    def wrapper(*a, **k):
        try:
            return f(*a, **k)
        except OSError as err:
            return err
    return wrapper


########################################################################
##### ConfigParser with Comments and Header
from configparser import ConfigParser

class ConfigParserWithComments(ConfigParser):
    def __init__(self, header):
        self._header = header
        self.optionxform = str
        super(ConfigParser, self).__init__()

    def write(self, fp):
        if self._header:
            fp.write('{}\n\n'.format(self._header))
        if self._defaults:
            fp.write('[{}]\n'.format(ConfigParser.DEFAULTSECT))
            for (key, value) in self._defaults.items():
                self._write_item(fp, key, value)
            fp.write('\n')
        for section in self._sections:
            fp.write('[{}]\n'.format(section))
            for (key, value) in self._sections[section].items():
                self._write_item(fp, key, value)
            fp.write('\n')

    def _write_item(self, fp, key, value):
        if key == '#' and value:
            for l in value.split('\n'):
                fp.write('# {}\n'.format(l))
        else:
            fp.write('{}: {}\n'.format(key, str(value).replace('\n', '\n\t')))


########################################################################
##### PathContents
class PathContents:
    def __init__(self, fs, basepath):
        self.basepath = basepath
        self.__entries = dict()
        for f in fs:
            try:
                if islink(f):
                    self.__entries[f] = (f, 0, '')
                elif isdir(f):
                    self.__entries[f] = (f, getsize(f), '')
                    self.__fill_contents(f)
                else:
                    self.__entries[f] = (f, getsize(f), '')
            except OSError as err:
                self.__entries[f] = (f, 0, self.__format_err(f, err))
        self.__entries = sorted(self.__entries.values())
        self.length = len(fs)
        self.tlength = len(self.__entries)
        self.tsize = sum([f[1] for f in self.__entries]) or 1

    def __fill_contents(self, path):
        for root, dirs, files in os.walk(path, topdown=False, onerror=self.__on_error):
            for f in dirs + files:
                fullpath = join(root, f)
                try:
                    if islink(fullpath):
                        self.__entries[fullpath] = (fullpath, 0, '')
                    else:
                        self.__entries[fullpath] = (fullpath, getsize(fullpath), '')
                except OSError as err:
                    self.__entries[fullpath] = (fullpath, 0, self.__format_err(fullpath, err))

    def __on_error(self, err):
        fullpath = join(self.basepath, err.filename)
        self.__entries[fullpath] = (fullpath, 0, self.__format_err(fullpath, err))

    def __format_err(self, filename, err):
        return Exception('[Errno {}] {}: \'{}\''.format(err.errno, err.strerror, filename.replace(self.basepath, '')))

    def __repr__(self):
        return 'PathContents[Base:"{}" with {} entries (Total: {} items, {:.2f} KB)]' \
            .format(self.basepath, self.length, self.tlength, self.tsize/1024)

    def remove_files(self, fs):
        new, size = list(), 0
        for f, s, e in self.__entries:
            if f not in fs:
                new.append((f, s, e))
                size += s
        self.__entries = new
        self.length = self.length # not really, but not important either
        self.tlength = len(self.__entries)
        self.tsize = size

    @property
    def entries(self):
        return sorted(self.__entries, reverse=False)

    @property
    def entries_rev(self):
        return sorted(self.__entries, reverse=True)


########################################################################
##### DirsTree
class DirsTree:
    def __init__(self, path, dotfiles):
        self._dotfiles = dotfiles
        self.build(path)

    def __get_graph(self, path):
        """return a OrderedDict with tree structure"""
        d, expanded = dict(), None
        while path:
            if path==os.sep and os.sep in d:
                break
            d[path] = (get_dirs(path, self._dotfiles), expanded)
            expanded = basename(path)
            path = dirname(path)
        return OrderedDict(sorted(d.items(), key=lambda t: t[0]))

    def __get_node(self, i, td, parent):
        """expand branch. Each node has (name, depth, fullname))"""
        dirs, expanded_node = td[list(td.keys())[i]]
        if not expanded_node:
            return list()
        lst = list()
        for d in dirs:
            lst.append((d, i, join(parent, d)))
            if d == expanded_node:
                lst2 = self.__get_node(i+1, td, join(parent, d))
                if lst2 is not None:
                    lst.extend(lst2)
        return lst

    def __getitem__(self, i):
        return self._data[i]

    def __len__(self):
        return len(self._data)

    def build(self, path):
        """build list with tree structure"""
        td = self.__get_graph(path)
        self._data = [(os.sep, -1, os.sep)]
        self._data.extend(self.__get_node(0, td, os.sep))
        self.path = path

    def regenerate_from_pos(self, newpos):
        """regenerate tree when changing to a new directory and return it"""
        newpath = self._data[newpos][2]
        self.build(newpath)
        return newpath

    @property
    def pos(self):
        """return position of current dir"""
        for i in range(len(self._data)):
            if self.path == self._data[i][2]:
                return i
        else:
            return -1

    @property
    def cur_depth(self):
        return self.get_depth(self.pos)

    def get_depth(self, pos):
        return self._data[pos][1]

    @property
    def is_first_sibling(self):
        return self.cur_depth != self.get_depth(self.pos-1)

    @property
    def first_sibling_pos(self):
        newpos = self.pos
        while True:
            if newpos-1 < 0 or self.cur_depth != self.get_depth(newpos-1):
                break
            newpos -= 1
        return newpos

    @property
    def is_last_sibling(self):
        return self.cur_depth != self.get_depth(self.pos+1)

    @property
    def last_sibling_pos(self):
        newpos = self.pos
        while True:
            if newpos+1 == len(self) or self.cur_depth != self.get_depth(newpos+1):
                break
            newpos += 1
        return newpos

    @property
    def parent_pos(self):
        for i in range(self.pos-1, -1, -1):
            if self.get_depth(i) == self.cur_depth-1:
                break
        return i

    @property
    def has_children_dirs(self):
        return len(get_dirs(self.path, self._dotfiles)) > 0

    def to_child(self):
        newpath = None
        child_dirs = get_dirs(self.path, self._dotfiles)
        if len(child_dirs) > 0:
            newpath = join(self.path, child_dirs[0])
            self.build(newpath)
        return newpath

    def show_tree(self, a=0, z=-1):
        """show an ascii representation of the tree. Not used in lfm"""
        if z>len(self._data) or z==-1:
            z = len(self._data)
        for i in range(a, z):
            name, depth, fullname = self._data[i]
            if fullname == self.path:
                name += ' <====='
            if name == os.sep:
                print(' ' + name)
            else:
                print(' | ' * depth + ' +- ' + name)


########################################################################
##### Paths
def get_realpath(tab):
    if tab.fs[tab.i].is_link:
        try:
            return '-> ' + os.readlink(join(tab.dirname, tab.current_filename))
        except OSError:
            return tab.fs.path_str + '/' + tab.current_filename
    else:
        return tab.fs.path_str + '/' + tab.current_filename

def get_relpath(path, base):
    return relpath(path, base) if path.startswith(base) else path

def get_norm_path(path, basedir):
    path = expandvars(expanduser(path))
    path = path if isabs(path) else join(basedir, path)
    return normpath(path)

def get_dir_size(dirname):
    try:
        buf = check_output(['du', '-sb', dirname], stderr=STDOUT, universal_newlines=True)
        return int(buf.split()[0])
    except:
        return -1

def get_dirs(path, dotfiles):
    try:
        if dotfiles:
            ds = [d for d in os.listdir(path) if isdir(join(path, d))]
        else:
            ds = [d for d in os.listdir(path) if d[0]!='.' and isdir(join(path, d))]
    except OSError:
        return list()
    return sorted(ds)


########################################################################
##### Files
def get_filetype(pfile):
    """Returns the type of a file as FileType"""
    lmode = os.lstat(pfile).st_mode
    if stat.S_ISDIR(lmode):
        return FileType.dir
    if stat.S_ISLNK(lmode):
        try:
            mode = os.stat(pfile)[stat.ST_MODE]
        except OSError:
            return FileType.nlink
        else:
            return FileType.link2dir if stat.S_ISDIR(mode) else FileType.link
    if stat.S_ISCHR(lmode):
        return FileType.cdev
    if stat.S_ISBLK(lmode):
        return FileType.bdev
    if stat.S_ISFIFO(lmode):
        return FileType.fifo
    if stat.S_ISSOCK(lmode):
        return FileType.socket
    if stat.S_ISREG(lmode) and (lmode & 0o111):
        return FileType.exe
    else:
        return FileType.reg # if no other type, regular file

def get_file_info(filename):
    try:
        return check_output(['file', '-b', filename], stderr=STDOUT, universal_newlines=True).strip()
    except:
        return 'no type information'

def backup_file(src, backup_ext):
    dest = src + backup_ext
    if exists(dest):
        raise FileExistsError('Cannot backup file:\n"{}" already exists'.format(dest))
    try:
        return copy_bulk(src, dest)
    except OSError as err:
        raise Exception('Cannot backup file:\n{}'.format(err))

def get_file_diff(file_old, file_new, diff_type):
    try:
        d0 = datetime.fromtimestamp(os.stat(file_old).st_mtime)
        date_old = d0.strftime('    %Y-%m-%d %H:%M:%S.%f ') + tzname[0]
        d1 = datetime.fromtimestamp(os.stat(file_new).st_mtime)
        date_new = d1.strftime('    %Y-%m-%d %H:%M:%S.%f ') + tzname[0]
        # with open(file_old).readlines() as buf0, open(file_new).readlines() as buf1:
        with open(file_old) as f0, open(file_new) as f1:
            buf0, buf1 = f0.readlines(), f1.readlines()
            if diff_type == 'context':
                diff = difflib.context_diff(buf0, buf1, file_old, file_new, date_old, date_new)
            elif diff_type == 'unified':
                diff = difflib.unified_diff(buf0, buf1, file_old, file_new, date_old, date_new)
            elif diff_type == 'ndiff':
                diff = difflib.ndiff(buf0, buf1)
            return ''.join(diff)
    except:
        return ''

def copy_file(filename, basepath, destdir, overwrite=False):
    partial = filename.replace(basepath, '')
    dest = join(destdir, partial) if isdir(destdir) else destdir
    try:
        dest_exists = exists(dest)
        if dest_exists and not overwrite:
            raise LFMFileExistsError(dest)
        if islink(filename) or isfile(filename):
            if dest_exists:
                os.unlink(dest)
            copy2(filename, dest, follow_symlinks=False)
        elif isdir(filename):
            if dest_exists:
                try:
                    os.rmdir(dest)
                except OSError as err:
                    if err.errno != errno.ENOTEMPTY: # Directory not empty
                        raise
            try:
                os.mkdir(dest)
            except OSError as err:
                if err.errno != errno.EEXIST: # File exists
                    raise
            try:
                st = os.lstat(src)
                os.chown(dest, st[stat.ST_UID], st[stat.ST_GID])
                copystat(src, dest, follow_symlinks=False)
            except:
                pass
        else:
            raise Exception('Cannot copy file!\nCannot copy special file: \'{}\''.format(partial))
    except OSError as err:
        raise Exception('Cannot copy file!\n[Errno {}] {}: \'{}\''.format(err.errno, err.strerror, partial))

def move_file(filename, basepath, destdir, overwrite=False):
    # alternative method instead of copy & delete. Faster but less control
    partial = filename.replace(basepath, '')
    dest = join(destdir, partial) if isdir(destdir) else destdir
    try:
        if exists(dest) and not overwrite:
            raise LFMFileExistsError(dest)
        move(filename, dest)
    except OSError as err:
        raise Exception('Cannot move file!\n[Errno {}] {}: \'{}\''.format(err.errno, err.strerror, partial))

def delete_file(filename, basepath):
    try:
        if islink(filename):
            os.unlink(filename)
        elif isdir(filename):
            os.rmdir(filename)
        else:
            os.unlink(filename)
    except OSError as err:
        raise Exception('Cannot delete file!\n[Errno {}] {}: \'{}\''.format(err.errno, err.strerror, filename.replace(basepath, '')))

@catch_os_exception
def make_dir(newdir):
    os.makedirs(newdir)

@catch_os_exception
def touch_file(filename):
    with open(filename, 'a'):
        os.utime(filename)

@catch_os_exception
def rename_file(src, dest):
    os.rename(src, dest)

@catch_os_exception
def link_create(linkname, pointto):
    os.symlink(pointto, linkname)

@catch_os_exception
def link_edit(linkname, pointto):
    os.unlink(linkname)
    os.symlink(pointto, linkname)


##### copy, overwrite, delete
def copy_bulk(src, dest):
    if isdir(src):
        copytree(src, dest, symlinks=True)
    elif isfile(src):
        copy2(src, dest)

def overwrite_vfsfile(src, dest):
    copystat(dest, src) # copy attrs
    move(src, dest)

def delete_bulk(path, ignore_errors=False):
    if isdir(path):
        rmtree(path, ignore_errors=ignore_errors)
    elif isfile(path):
        if ignore_errors:
            try:
                os.unlink(path)
            except OSError:
                pass
        else:
            os.unlink(path)


########################################################################
##### Un/compress
from compress import get_compressed_file_engine, packagers_by_type, PackagerTAR

def uncompress_dir(filename, destdir):
    if not isfile(filename):
        raise Exception('It\'s not a file: {}'.format(basename(filename)))
    c = get_compressed_file_engine(filename)
    if c is None:
        raise Exception('Cannot uncompress this file type: {}'.format(basename(filename)))
    res, err = run_in_cli(c.cmd_uncompress, destdir)
    if err:
        raise Exception(err)
    return res

def compress_dir(dir, typ):
    if not isdir(dir):
        raise Exception('It\'s not a directory: {}'.format(basename(dir)))
    c = packagers_by_type[typ](dir)
    if c is None:
        raise Exception('Cannot compress: {}'.format(basename(dir)))
    res, err = run_in_cli(c.cmd_compress, dirname(dir))
    if err:
        raise Exception(err)
    return res

def compress_uncompress_file(filename, typ):
    if not isfile(filename):
        raise Exception('It\'s not a file: {}'.format(basename(filename)))
    c = get_compressed_file_engine(filename)
    if c is None or isinstance(c, PackagerTAR):
        cmd = packagers_by_type[typ](filename).cmd_compress
    elif c.type == typ:
        cmd = c.cmd_uncompress
    else:
        raise Exception('Cannot un/compress \'{}\' with type {}'.format(basename(filename), typ))
    res, err = run_in_cli(cmd, dirname(filename))
    if err:
        raise Exception(err)
    return res


########################################################################
##### FileSystems
def get_filesystems_info():
    return check_output(['df', '-h'], stderr=STDOUT, universal_newlines=True)

def get_mount_points():
    """return system mount points as list of (mountpoint, device, fstype).
    Compatible with linux and solaris"""
    buf = check_output(['mount'], stderr=STDOUT, universal_newlines=True).strip()
    lst = [(e.split()[2], e.split()[0], e.split()[4]) for e in buf.split('\n')]
    return sorted(lst, reverse=True)

def get_mountpoint_for_file(filename):
    try:
        for m, d, t in get_mount_points():
            if filename.find(m) != -1:
                return (m, d, t)
        else:
            raise
    except:
        return ('/', '<unknown>', '<unknown>')


########################################################################
##### Users & Groups
def get_user_fullname(user):
    try:
        return pwd.getpwnam(user)[4]
    except KeyError:
        return '<unknown user name>'

def get_owners():
    """get a list with the users defined in the system"""
    return sorted([e[0] for e in pwd.getpwall()])

def get_groups():
    """get a list with the groups defined in the system"""
    return sorted([e[0] for e in grp.getgrall()])


########################################################################
##### Binary programs
def get_binary_programs():
    return sorted({f for p in os.getenv('PATH').split(':') if isdir(p) for f in os.listdir(p) if isfile(join(p, f))})


########################################################################
##### String formatting
def size2str(size):
    """Converts a file size into a string"""
    if size >= 1000000000:
        return str(size//1048576) + 'M' # 1024*1024
    elif size >= 10000000:
        return str(size//1024) + 'K'
    else:
        return str(size)

def num2str(num):
    # Thanks to "Fatal" in #pys60
    num = str(num)
    return (len(num) < 4) and num or (num2str(num[:-3])+","+num[-3:])

def time2str(t, short=True):
    """Converts a file time into a string"""
    if -15552000 < (time() - t) < 15552000:
        # date < 6 months from now, past or future
        fmt = '%d %b %H:%M' if short else '%a %b %d %H:%M'
    else:
        fmt = '%d %b  %Y' if short else '%a  %d %b %Y'
    return strftime(fmt, localtime(t))

def time2str_full(t):
    return asctime(localtime(t))

def perms2str(perms):
    """Converts a file permisions into a string"""
    return stat.filemode(perms)[1:].lower()

def type2str(ftype):
    """Converts a file type into a string"""
    return FILETYPES[ftype][0]

def rdev2str(rdev):
    """Converts a device file numbers into a string"""
    return ('%d,%d' % rdev).rjust(7)

def owner2str(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)

def group2str(gid):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)

def str2perms(perms):
    ps = 0
    for i, p in enumerate(reversed(perms)):
        if p == 'x':
            ps += 1 * 8**(i//3)
        elif p == 'w':
            ps += 2 * 8**(i//3)
        elif p == 'r':
            ps += 4 * 8**(i//3)
        elif p == 't' and i == 0:
            ps += 1 * 8**3
        elif p == 's':
            if i == 6:
                ps += 4 * 8**3
            elif i == 3:
                ps += 2 * 8**3
    return ps


########################################################################
##### Support for wide chars
def length(text):
    return wchar_len(text) if use_wide_chars else len(text)

def max_length(entries):
    return max(map(wchar_len if use_wide_chars else len, entries))

def text2wrap(*args, **kw):
    return text2wrap_wchar(*args, **kw) if use_wide_chars else text2wrap_normal(*args, **kw)

def text2wrap_normal(text, max_width, ljust=True, start_pct=.66, sep='~', fill=True):
    """Returns a displayable string from an attribute"""
    length = len(text)
    if length <= max_width:
        if ljust:
            return text.ljust(max_width) if fill else text
        else:
            return text.ljust(max_width) if ljust else text.rjust(max_width)
    else:
        until = int(max_width*start_pct)
        return text[:until] + sep + text[-(max_width-until-1):]

def text2wrap_wchar(text, max_width, ljust=True, start_pct=.66, sep='~', fill=True):
    """Returns a displayable string from an attribute"""
    length = wchar_len(text)
    if length <= max_width:
        if ljust:
            return wchar_ljust(text, max_width) if fill else text
        else:
            return wchar_ljust(text, max_width) if ljust else wchar_rjust(text, max_width)
    else:
        return wchar_fill(text, max_width, start_pct, sep)

def wchar_len(text):
    libc = CDLL('libc.so.6')
    # assert libc.wcswidth('世界')==4
    return len(text) if len(text)>127 else libc.wcswidth(text) # BUG: wcswidth doesn't accept string with 128+ chars

def wchar_ljust(text, max_width):
    return text + ' '*(max_width-wchar_len(text))

def wchar_rjust(text, max_width):
    return ' '*(max_width-wchar_len(text)) + text

def wchar_fill(text, max_width, pct, sep):
    pos = int(max_width*pct)
    buf1 = buf2 = ''
    for c in text:
        if wchar_len(buf1) + wchar_len(c) > pos:
            break
        buf1 += c
    buf1 += sep
    len_buf1 = wchar_len(buf1)
    for c in text[::-1]:
        if len_buf1 + wchar_len(c) + wchar_len(buf2) > max_width:
            break
        buf2 += c
    return buf1+buf2[::-1]


########################################################################
##### Navigate through paths
stepchars = whitespace + punctuation

def prev_step(text, pos):
    pos = max(0, pos-2)
    while pos > 0 and text[pos] not in stepchars:
        pos -=1
    return pos+1 if pos > 0 else 0

def next_step(text, pos):
    pos += 1
    l = len(text)
    while pos < l and text[pos] not in stepchars:
        pos +=1
    return pos+1 if pos < l else l


########################################################################
##### Running commands in shell
import curses

def escape_str(buf):
    if buf.find('"') != -1:
        return '\'{}\''.format(buf.replace('"', '\\"'))
    else:
        return '"{}"'.format(buf)

def escape_command(cmd, filename, background):
    filename = filename.replace('$', '\$')
    return '{} {}{}'.format(cmd, escape_str(filename), ' >/dev/null 2>&1 &' if background else '')

def run_on_current_file(program, filename, background=False):
    curses.endwin()
    os.system(escape_command(program, filename, background))
    curses.curs_set(0)

def run_in_background(cmd, path):
    cmd = 'cd {} && {} >/dev/null 2>&1 &'.format(escape_str(path), cmd)
    curses.endwin()
    os.system(cmd)
    curses.curs_set(0)

def run_shell(shell, path):
    curses.endwin()
    os.system('cd "{}" && {}'.format(path.replace('"', '\\"'), shell))
    curses.curs_set(0)

def run_in_cli(cmd, path):
    return Popen(cmd, shell=True, cwd=path, stdout=PIPE, stderr=PIPE, universal_newlines=True).communicate()


######################################################################
##### Process classes
from ui_widgets import CursorAnimation, DialogConfirm, DialogConfirmAll, DialogConfirmAllNone, \
                       DialogError, DialogMessagePanel, DialogProgress1Panel, DialogProgress2Panel

##### ProcessCommand
class ProcessCommand:
    def __init__(self, title, subtitle, cmd, path=None):
        self.title = title
        self.subtitle = subtitle
        self.cmd = cmd
        self.path = path
        self.proc = None
        self.status = None
        self.dialog = DialogMessagePanel(self.title, self.subtitle)
        self.animation = CursorAnimation()

    def check_stop(self):
        if self.dialog.check_key() == 0x03:
            self.proc.send_signal(SIGSTOP)
            self.dialog.hide()
            if DialogConfirm('Stop process', '{} {}'.format(self.title, self.subtitle), 0) == 1:
                self.proc.kill()
                return True
            else:
                self.dialog.show()
                self.proc.send_signal(SIGCONT)
        return False

    def run(self):
        self.dialog.show()
        results, errors = None, None
        self.proc = Popen(self.cmd, shell=True, cwd=self.path, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        if self.proc.poll(): # process can finish too fast
            while True:
                self.animation.next()
                self.status = self.proc.poll()
                if self.status is not None:
                    break
                if self.check_stop():
                    self.status = -100
                    break
                sleep(0.05)
        self.dialog.hide()
        results, errors = self.proc.communicate()
        return self.status, results, errors


##### ProcessFuncLoop
class ProcessFuncLoop:
    def __init__(self, title, fn, lst):
        self.title = title
        self.fn = fn
        self.lst = lst
        self.i, self.n = 0, len(lst)
        self.proc = None
        self.animation = CursorAnimation()

    def check_stop(self):
        if self.dialog.check_key() == 0x03:
            os.kill(self.proc.pid, SIGSTOP)
            self.dialog.hide()
            if DialogConfirm('Stop process', 'Stop "{}"?'.format(self.title), 0) == 1:
                os.kill(self.proc.pid, SIGKILL)
                return True
            else:
                self.dialog.show()
                os.kill(self.proc.pid, SIGCONT)
        return False

    def run_func(self, fn, qin, qout, qerr, conn):
        while not qin.empty():
            if qin.empty():
                break
            try:
                ret = self.do_run(fn, qin, conn)
            except Exception as err:
                qout.put_nowait(None)
                qerr.put_nowait(err)
                if not isinstance(err, LFMFileSkipped):
                    conn.send((ProcCode.error, str(err)))
            else:
                qout.put_nowait(ret)
                qerr.put_nowait(None)
            # sleep(0.001)
        conn.send((ProcCode.end, ))
        sleep(0.25)

    def run(self):
        self.prepare()
        self.dialog.show()
        qin, qout, qerr = Queue(maxsize=self.n), Queue(maxsize=self.n), Queue(maxsize=self.n)
        for a in self.lst:
            qin.put(a)
        conn_parent, conn_child = Pipe()
        self.proc = Process(target=self.run_func, args=(self.fn, qin, qout, qerr, conn_child))
        self.proc.start()
        while True:
            if conn_parent.poll():
                buf = conn_parent.recv()
                if buf[0] == ProcCode.end:
                    conn_parent.send(ProcCodeConfirm.stop)
                    status = ProcCode.end
                    rets, errs = list(), list()
                    while not qout.empty():
                        rets.append(qout.get_nowait())
                    while not qerr.empty():
                        errs.append(qerr.get_nowait())
                    break
                elif buf[0] == ProcCode.error:
                    self.dialog.hide()
                    msg = buf[1] if buf[1].startswith('Cannot') else 'Cannot {}!\n{}'.format(self.title.lower(), buf[1])
                    DialogError(msg)
                    self.dialog.show()
                elif buf[0] == ProcCode.next:
                    self.display_next(*buf[1:])
                    ans = self.confirm_pre()
                    conn_parent.send(ans)
                    if ans == ProcCodeConfirm.stop:
                        status, rets, errs = ProcCode.stopped, None, None
                        break
                elif buf[0] == ProcCode.confirm:
                    ans = self.confirm_post(buf[1])
                    conn_parent.send(ans)
                    if ans == ProcCodeConfirm.stop:
                        status, rets, errs = ProcCode.stopped, None, None
                        break
            if self.check_stop():
                status, rets, errs = ProcCode.stopped, None, None
                break
            self.animation.next()
            # sleep(0.05)
        self.dialog.hide()
        try:
            os.kill(self.proc.pid, SIGKILL)
        except ProcessLookupError:
            pass
        return status, rets, errs

    def prepare(self):
        self.dialog = DialogProgress1Panel(self.title)

    def display_next(self, text, *args):
        self.i += 1
        self.dialog.update(text, self.i, self.n)

    def confirm_pre(self):
        return ProcCodeConfirm.ok

    def confirm_post(self, *args):
        return ProcCodeConfirm.ok

    def do_run(self, fn, qin, conn):
        args = qin.get_nowait()
        conn.send((ProcCode.next, args[0]))
        _ = conn.recv()
        return fn(*args)


##### ProcessFuncDeleteLoop
class ProcessFuncDeleteLoop(ProcessFuncLoop):
    def __init__(self, title, fn, lst, tot_size, confirm):
        super(ProcessFuncDeleteLoop, self).__init__(title, fn, lst)
        self.tot_size = tot_size
        self.confirm = confirm

    def prepare(self):
        self.dialog = DialogProgress2Panel(self.title)
        self.acc_size = 0

    def display_next(self, text, size, *args):
        self.i += 1
        self.acc_size += size
        self.cur_elm = text
        self.dialog.update(text, self.i, self.n, self.acc_size, self.tot_size)

    def confirm_pre(self):
        if self.confirm:
            self.dialog.hide()
            ans = DialogConfirmAll(self.title, 'Delete \'{}\'?'.format(self.cur_elm), default=1)
            if ans == 1:
                ret = ProcCodeConfirm.ok
            elif ans == 2:
                self.confirm = False
                ret = ProcCodeConfirm.ok
            elif ans == 0:
                ret = ProcCodeConfirm.skip
            else: # ans == -1
                ret = ProcCodeConfirm.stop
            self.dialog.show()
            return ret
        else:
            return ProcCodeConfirm.ok

    def do_run(self, fn, qin, conn):
        filename, size, err, basepath = qin.get_nowait()
        conn.send((ProcCode.next, filename.replace(basepath, ''), size))
        ans = conn.recv()
        if err:
            raise err
        if ans == ProcCodeConfirm.ok:
            return fn(filename, basepath)
        elif ans == ProcCodeConfirm.skip:
            raise LFMFileSkipped(filename)
        else:
            return None


##### ProcessFuncCopyLoop
class ProcessFuncCopyLoop(ProcessFuncLoop):
    def __init__(self, title, fn, lst, tot_size, confirm_overwrite):
        super(ProcessFuncCopyLoop, self).__init__(title, fn, lst)
        self.tot_size = tot_size
        self.overwrite = None if confirm_overwrite else ProcCodeConfirm.ok

    def prepare(self):
        self.dialog = DialogProgress2Panel(self.title)
        self.acc_size = 0

    def display_next(self, text, size, *args):
        self.i += 1
        self.acc_size += size
        self.cur_elm = text
        self.dialog.update(text, self.i, self.n, self.acc_size, self.tot_size)

    def confirm_post(self, filename):
        if self.overwrite is None:
            self.dialog.hide()
            ans = DialogConfirmAllNone(self.title, 'Overwrite \'{}\'?'.format(filename), default=1)
            if ans == 1:
                ret = ProcCodeConfirm.ok
            elif ans == 2:
                ret = self.overwrite = ProcCodeConfirm.ok
            elif ans == 0:
                ret = ProcCodeConfirm.skip
            elif ans == -2:
                ret = self.overwrite = ProcCodeConfirm.skip
            else: # ans == -1
                ret = ProcCodeConfirm.stop
            self.dialog.show()
            return ret
        else:
            return self.overwrite

    def do_run(self, fn, qin, conn):
        filename, size, err, basepath, destdir = qin.get_nowait()
        conn.send((ProcCode.next, filename.replace(basepath, ''), size))
        ans = conn.recv()
        if err:
            raise err
        if ans == ProcCodeConfirm.ok:
            try:
                return fn(filename, basepath, destdir)
            except LFMFileExistsError as err:
                conn.send((ProcCode.confirm, err))
                ans = conn.recv()
                if ans == ProcCodeConfirm.ok:
                    return fn(filename, basepath, destdir, overwrite=True)
                elif ans == ProcCodeConfirm.skip:
                    raise LFMFileSkipped(filename)
                else:
                    return None
        else:
            return None


########################################################################
