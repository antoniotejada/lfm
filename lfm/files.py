# -*- coding: utf-8 -*-

"""files.py

This module defines files utilities for lfm.
"""


import sys
import os
import os.path
import stat
import time
import pwd
import grp
import tempfile

from utils import get_shell_output2


########################################################################
##### constants
# File Type:    dir, link to directory, link, nlink, char dev,
#               block dev, fifo, socket, executable, file
(FTYPE_DIR, FTYPE_LNK2DIR, FTYPE_LNK, FTYPE_NLNK, FTYPE_CDEV, FTYPE_BDEV,
 FTYPE_FIFO, FTYPE_SOCKET, FTYPE_EXE, FTYPE_REG) = xrange(10)

FILETYPES = { FTYPE_DIR: (os.sep, 'Directory'),
              FTYPE_LNK2DIR: ('~', 'Link to Directory'),
              FTYPE_LNK: ('@', 'Link'), FTYPE_NLNK: ('!', 'No Link'),
              FTYPE_CDEV: ('-', 'Char Device'), FTYPE_BDEV: ('+', 'Block Device'),
              FTYPE_FIFO: ('|', 'Fifo'), FTYPE_SOCKET: ('#', 'Socket'),
              FTYPE_EXE: ('*', 'Executable'), FTYPE_REG: (' ', 'File') }

(FT_TYPE, FT_PERMS, FT_OWNER, FT_GROUP, FT_SIZE, FT_MTIME) = xrange(6)

# Sort Type:    None, byName, bySize, byDate, byType
(SORTTYPE_None, SORTTYPE_byName, SORTTYPE_byName_rev, SORTTYPE_bySize,
 SORTTYPE_bySize_rev, SORTTYPE_byDate, SORTTYPE_byDate_rev) = xrange(7)


########################################################################
##### general functions
# HACK: checks for st_rdev in stat_result, falling back to
#       "ls -la %s" hack if Python before 2.2 or without st_rdev
try:
    os.stat_result.st_rdev
except AttributeError:
    def get_rdev(f):
        """'ls -la' to get mayor and minor number of devices"""
        try:
            buf = os.popen('ls -la %s' % f).read().split()
        except:
            return 0
        else:
            try:
                return int(buf[4][:-1]), int(buf[5])
            except:
                # HACK: found 0xff.. encoded device numbers, ignore them...
                return 0, 0
else:
    def get_rdev(f):
        """mayor and minor number of devices"""
        r = os.stat(f).st_rdev
        return r >> 8, r & 255


def __get_size(f):
    """return the size of the directory or file via 'du -sk' command"""

    buf = get_shell_output2('du -sk \"%s\"' % f)
    if buf:
        return int(buf.split()[0]) * 1024
    else:
        return 0


def get_realpath(path, filename, filetype):
    """return absolute path or, if path is a link, pointed file"""

    if filetype in (FTYPE_LNK2DIR, FTYPE_LNK, FTYPE_NLNK):
        try:
            return '-> ' + os.readlink(os.path.join(path, filename))
        except os.error:
            return os.path.join(path, filename)
    else:
        return os.path.join(path, filename)


def get_linkpath(path, filename):
    """return absolute path to the destination of a link"""

    link_dest = os.readlink(os.path.join(path, filename))
    return os.path.normpath(os.path.join(path, link_dest))


def join(directory, f):
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    return os.path.join(directory, f)


def __get_filetype(f):
    """get the type of the file. See listed types above"""

    f = os.path.abspath(f)
    lmode = os.lstat(f)[stat.ST_MODE]
    if stat.S_ISDIR(lmode):
        return FTYPE_DIR
    if stat.S_ISLNK(lmode):
        try:
            mode = os.stat(f)[stat.ST_MODE]
        except OSError:
            return FTYPE_NLNK
        else:
            if stat.S_ISDIR(mode):
                return FTYPE_LNK2DIR
            else:
                return FTYPE_LNK
    if stat.S_ISCHR(lmode):
        return FTYPE_CDEV
    if stat.S_ISBLK(lmode):
        return FTYPE_BDEV
    if stat.S_ISFIFO(lmode):
        return FTYPE_FIFO
    if stat.S_ISSOCK(lmode):
        return FTYPE_SOCKET
    if stat.S_ISREG(lmode) and (lmode & 0111):
        return FTYPE_EXE
    else:
        return FTYPE_REG       # if no other type, regular file


def get_fileinfo(f, pardir_flag = False, show_dirs_size = False):
    """return information about a file in next format:
    (filetype, perms, owner, group, size, mtime)"""

    st = os.lstat(f)
    typ = __get_filetype(f)
    if typ in (FTYPE_DIR, FTYPE_LNK2DIR) and not pardir_flag and show_dirs_size:
        size = __get_size(f)
    elif typ in (FTYPE_CDEV, FTYPE_BDEV):
        # HACK: it's too time consuming to calculate all files' rdevs
        #       in a directory, so we just calculate what we need
        #       at show time
        # maj_red, min_rdev = get_rdev(file)
        size = 0
    else:
        size = st[stat.ST_SIZE]
    try:
        owner = pwd.getpwuid(st[stat.ST_UID])[0]
    except:
        owner = str(st[stat.ST_UID])
    try:
        group = grp.getgrgid(st[stat.ST_GID])[0]
    except:
        group = str(st[stat.ST_GID])
    return (typ, stat.S_IMODE(st[stat.ST_MODE]), owner, group,
            size, st[stat.ST_MTIME])


def perms2str(p):
    permis = ['x', 'w', 'r']
    perms = ['-'] * 9
    for i in xrange(9):
        if p & (0400 >> i):
            perms[i] = permis[(8-i) % 3]
    if p & 04000:
        perms[2] = 's'
    if p & 02000:
        perms[5] = 's'
    if p & 01000:
        perms[8] = 't'
    return ''.join(perms)


def get_fileinfo_dict(path, filename, filevalues):
    """return a dict with file information"""

    res = {}
    res['filename'] = filename
    typ = filevalues[FT_TYPE]
    res['type_chr'] = FILETYPES[typ][0]
    if typ == (FTYPE_CDEV, FTYPE_BDEV):
        # HACK: it's too time consuming to calculate all files' rdevs
        #       in a directory, so we just calculate needed ones here
        #       at show time
        maj_rdev, min_rdev = get_rdev(os.path.join(path, filename))
        res['size'] = 0
        res['maj_rdev'] = maj_rdev
        res['min_rdev'] = min_rdev
        res['dev'] = 1
    else:
        size = filevalues[FT_SIZE]
        if size >= 1000000000L:
            size = str(size/(1024*1024)) + 'M'
        elif size >= 10000000L:
            size = str(size/1024) + 'K'
        else:
            size = str(size)
        res['size'] = size
        res['maj_rdev'] = 0
        res['min_rdev'] = 0
        res['dev'] = 0
    res['perms'] = perms2str(filevalues[1])
    res['owner'] = filevalues[FT_OWNER]
    res['group'] = filevalues[FT_GROUP]
    if -15552000 < (time.time() - filevalues[FT_MTIME]) < 15552000:
        # filedate < 6 months from now, past or future
        mtime = time.strftime('%a %b %d %H:%M', time.localtime(filevalues[FT_MTIME]))
        mtime2 = time.strftime('%d %b %H:%M', time.localtime(filevalues[FT_MTIME]))
    else:
        mtime = time.strftime('%a  %d %b %Y', time.localtime(filevalues[FT_MTIME]))
        mtime2 = time.strftime('%d %b  %Y', time.localtime(filevalues[FT_MTIME]))
    res['mtime'] = mtime
    res['mtime2'] = mtime2
    return res


def get_dir(path, show_dotfiles = 1):
    """return a dict whose elements are formed by file name as key
    and a (filetype, perms, owner, group, size, mtime) tuple as value"""

    path = os.path.normpath(path)
    files_dict = {}
    if path != os.sep:
        files_dict[os.pardir] = get_fileinfo(os.path.dirname(path), 1)
    files_list = os.listdir(path)
    if not show_dotfiles:
        files_list = [f for f in files_list if f[0] != '.']
    for f in files_list:
        files_dict[f] = get_fileinfo(os.path.join(path, f))
    return len(files_dict), files_dict


def get_owners():
    """get a list with the users defined in the system"""
    return [e[0] for e in pwd.getpwall()]


def get_user_fullname(user):
    """return the fullname of an user"""
    try:
        return pwd.getpwnam(user)[4]
    except KeyError:
        return '<unknown user name>'


def get_groups():
    """get a list with the groups defined in the system"""
    return [e[0] for e in grp.getgrall()]


def set_perms(f, perms):
    """set permissions to a file"""
    ps, i = 0, 8
    for p in perms:
        if p == 'x':
            ps += 1 * 8 ** int(i / 3)
        elif p == 'w':
            ps += 2 * 8 ** int(i / 3)
        elif p == 'r':
            ps += 4 * 8 ** int(i / 3)
        elif p == 't' and i == 0:
            ps += 1 * 8 ** 3
        elif p == 's' and (i == 6 or i == 3):
            if i == 6:
                ps += 4 * 8 ** 3
            else:
                ps += 2 * 8 ** 3
        i -= 1
    try:
        os.chmod(f, ps)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


def set_owner_group(f, owner, group):
    """set owner and group to a file"""
    try:
        owner_n = pwd.getpwnam(owner)[2]
    except:
        owner_n = int(owner)
    try:
        group_n = grp.getgrnam(group)[2]
    except:
        group_n = int(group)
    try:
        os.chown(f, owner_n, group_n)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)

def get_fs_info():
    """return a list containing the info returned by 'df -k', i.e,
    file systems size and occupation, in Mb. And the filesystem type:
    [dev, size, used, available, use%, mount point, fs type]"""

    try:
        buf = os.popen('df -k').readlines()
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)
    else:
        fs = []
        for l in buf:
            if l[0] == os.sep:
                e = l.split()
                if len(e) > 1:
                    e[1] = str(int(e[1]) / 1024)
                    e[2] = str(int(e[2]) / 1024)
                    e[3] = str(int(e[3]) / 1024)
                    e[4] = e[4]
                    e[5] = e[5]
                else:
                    continue
            elif l[0] == ' ':
                t = l.split()
                e.append(str(int(t[0]) / 1024))
                e.append(str(int(t[1]) / 1024))
                e.append(str(int(t[2]) / 1024))
                e.append(t[3])
                e.append(t[4])
            else:
                continue
            fs.append(e)

        # get filesystems type
        if sys.platform[:5] == 'linux':
            es = open('/etc/fstab').readlines()
            fstype_pos = 2
        elif sys.platform[:5] == 'sunos':
            es = open('/etc/vfstab').readlines()
            fstype_pos = 3
        else:
            es = []
        for f in fs:
            for e in es:
                if e.find(f[5]) != -1:
                    f.append(e.split()[fstype_pos])
                    break
            else:
                f.append('unknown')
        return fs


########################################################################
##### temporary file
def mktemp():
    return tempfile.mkstemp()[1]

def mkdtemp():
    return tempfile.mkdtemp()


########################################################################
##### sort
def __do_sort(f_dict, sortmode, sort_mix_cases):
    def __move_pardir_to_top(names):
        if names.count(os.pardir) != 0:
            names.remove(os.pardir)
            names.insert(0, os.pardir)
        return names

    if sortmode == SORTTYPE_None:
        names = f_dict.keys()
        return __move_pardir_to_top(f_dict)

    if sortmode in (SORTTYPE_byName, SORTTYPE_byName_rev):
        if sort_mix_cases:
            mycmp = lambda a, b: cmp(a.lower(), b.lower())
        else:
            mycmp = None
        names = f_dict.keys()
        names.sort(cmp=mycmp)
        if sortmode == SORTTYPE_byName_rev:
            names.reverse()
        return __move_pardir_to_top(names)

    mydict = {}
    for k in f_dict.keys():
        if sortmode in (SORTTYPE_bySize, SORTTYPE_bySize_rev):
            size = f_dict[k][FT_SIZE]
            while mydict.has_key(size):    # can't be 2 entries with same key
                size += 0.1
            mydict[size] = k
        elif sortmode in (SORTTYPE_byDate, SORTTYPE_byDate_rev):
            tim = f_dict[k][FT_MTIME]
            while mydict.has_key(tim):    # can't be 2 entries with same key
                tim += 0.1
            mydict[tim] = k
        else:
            raise ValueError
    values = mydict.keys()
    values.sort()
    names = [mydict[v] for v in values]
    if sortmode in (SORTTYPE_bySize_rev, SORTTYPE_byDate_rev):
        names.reverse()
    return __move_pardir_to_top(names)


def sort_dir(files_dict, sortmode, sort_mix_dirs, sort_mix_cases):
    """return an array of files which are sorted by mode"""

    # separate directories and files
    d, f = {}, {}
    if sort_mix_dirs:
        f = files_dict
    else:
        for k, v in files_dict.items():
            if v[FT_TYPE] in (FTYPE_DIR, FTYPE_LNK2DIR):
                d[k] = v
            else:
                f[k] = v
    # sort
    if d:
        d1 = __do_sort(d, sortmode, sort_mix_cases)
    else:
        d1 = []
    d2 = __do_sort(f, sortmode, sort_mix_cases)
    d1.extend(d2)
    return d1


########################################################################
##### complete
def complete(entrypath, panelpath):
    if not entrypath:
        path = panelpath
    elif entrypath[0] == os.sep:
        path = entrypath
    else:
        path = os.path.join(panelpath, entrypath)
    # get elements
    if os.path.isdir(path):
        basedir = path
        fs = os.listdir(path)
    else:
        basedir = os.path.dirname(path)
        start = os.path.basename(path)
        try:
            entries = os.listdir(basedir)
        except OSError:
            entries = []
        fs = [f for f in entries if f.find(start, 0) == 0]
    # sort files with dirs first
    d1, d2 = [], []
    for f in fs:
        if os.path.isdir(os.path.join(basedir, f)):
            d1.append(f + os.sep)
        else:
            d2.append(f)
    d1.sort()
    d2.sort()
    d1.extend(d2)
    return d1


########################################################################
##### actions
# link
def do_create_link(pointto, link):
    os.symlink(pointto, link)


def modify_link(pointto, linkname):
    try:
        os.unlink(linkname)
        do_create_link(pointto, linkname)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


def create_link(pointto, linkname):
    try:
        do_create_link(pointto, linkname)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


# copy
def do_copy(source, dest):
    import shutil

    if os.path.islink(source):
        dest = os.path.join(os.path.dirname(dest), os.path.basename(source))
        try:
            do_create_link(os.readlink(source), dest)
        except (IOError, os.error), (errno, strerror):
            return (strerror, errno)
    elif os.path.isdir(source):
        try:
            os.mkdir(dest)
        except (IOError, os.error), (errno, strerror):
            pass     # don't return if directory exists
        else:
#             # copy mode, times, owner and group
#             st = os.lstat(source)
#             os.chown(dest, st[stat.ST_UID], st[stat.ST_GID])
#             shutil.copymode(source, dest)
#             shutil.copystat(source, dest)
            pass
        for f in os.listdir(source):
            do_copy(os.path.join(source, f), os.path.join(dest, f))
    elif source == dest:
        raise IOError, (0, "Source and destination are the same file")
    else:
        shutil.copy2(source, dest)


def copy(f, path, destdir, check_fileexists = 1):
    """ copy file / dir to destdir"""

    fullpath = os.path.join(path, f)
    if destdir[0] != os.sep:
        destdir = os.path.join(path, destdir)
    if os.path.isdir(destdir):
        destdir = os.path.join(destdir, f)
    if os.path.exists(destdir) and check_fileexists:
        return os.path.basename(destdir)
    try:
        do_copy(fullpath, destdir)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


# move
def move(f, path, destdir, check_fileexists = 1):
    """delete file / dir"""

    fullpath = os.path.join(path, f)
    if destdir[0] != os.sep:
        destdir = os.path.join(path, destdir)
    if os.path.isdir(destdir):
        destdir = os.path.join(destdir, f)
    if os.path.exists(destdir) and check_fileexists:
        return os.path.basename(destdir)
    if os.path.dirname(fullpath) == os.path.dirname(destdir):
        try:
            os.rename(fullpath, destdir)
        except (IOError, os.error), (errno, strerror):
            return (strerror, errno)
        return
    try:
        do_copy(fullpath, destdir)
    except (IOError, os.error), (errno, strerror):
        try:
            do_delete(destdir)
        except (IOError, os.error), (errno, strerror):
            return (strerror, errno)
        else:
            return (strerror, errno)
    else:
        try:
            do_delete(fullpath)
        except (IOError, os.error), (errno, strerror):
            return (strerror, errno)


# delete
def do_delete(f):
    if os.path.islink(f):
        os.unlink(f)
    elif os.path.isdir(f):
        for f2 in os.listdir(f):
            do_delete(os.path.join(f, f2))
        os.rmdir(f)
    else:
        os.unlink(f)


def delete(f, path):
    """delete file / dir"""

    fullpath = os.path.join(path, f)
    try:
        do_delete(fullpath)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


# mkdir
def mkdir(path, newdir):
    """create directory"""

    fullpath = os.path.join(path, newdir)
    try:
        os.makedirs(fullpath)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


########################################################################
