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


########################################################################
########################################################################
def get_rdev(file):
    """return the size of the directory or file via 'du -sk' command
    or  via 'ls -la' to get mayor and minor number of devices."""

    # HACK: Python os.stat doesn't have rdev in returned tuple,
    #       which is a must to calculate major and minor numbers
    #       for devices
    # st_rdev = os.lstat(os.path.join(path, filename))[stat.ST_RDEV]
    try:
        str = os.popen('ls -la %s' % file).read().split()
    except:
        return 0
    else:
        return int(str[4][:-1]), int(str[5])


########################################################################
########################################################################
def __get_size(file):
    """return the size of the directory or file via 'du -sk' command"""

    i, o, e = os.popen3('du -sk \"%s\"' % file)
    buf = o.read(); err = e.read()
    i.close(); o.close(); e.close()
    # if an inner dir has problems return current size
    if not buf:
        return 0
    return int(buf.split()[0]) * 1024


########################################################################
########################################################################
def get_realpath(path, filename, filetype):
    """return absolute path or, if path is a link, pointed file"""

    if filetype == FTYPE_LNK2DIR or filetype == FTYPE_LNK or \
       filetype == FTYPE_NLNK:
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


########################################################################
########################################################################
def join(directory, file):
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    return os.path.join(directory, file)


########################################################################
########################################################################
# File Type:    dir, link to directory, link, nlink, char dev,
#               block dev, fifo, socket, executable, file
(FTYPE_DIR, FTYPE_LNK2DIR, FTYPE_LNK, FTYPE_NLNK, FTYPE_CDEV, FTYPE_BDEV,
 FTYPE_FIFO, FTYPE_SOCKET, FTYPE_EXE, FTYPE_REG) = range(10)

FILETYPES = { FTYPE_DIR: (os.sep, 'Directory'),
              FTYPE_LNK2DIR: ('~', 'Link to Directory'),
              FTYPE_LNK: ('@', 'Link'), FTYPE_NLNK: ('!', 'No Link'),
              FTYPE_CDEV: ('-', 'Char Device'), FTYPE_BDEV: ('+', 'Block Device'),
              FTYPE_FIFO: ('|', 'Fifo'), FTYPE_SOCKET: ('#', 'Socket'),
              FTYPE_EXE: ('*', 'Executable'), FTYPE_REG: (' ', 'File') }

def __get_filetype(file):
    """get the type of the file. See listed types above"""

    file = os.path.abspath(file)
    lmode = os.lstat(file)[stat.ST_MODE]
    if stat.S_ISDIR(lmode):
        return FTYPE_DIR
    if stat.S_ISLNK(lmode):
        try:
            mode = os.stat(file)[stat.ST_MODE]
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


(FT_TYPE, FT_PERMS, FT_OWNER, FT_GROUP, FT_SIZE, FT_MTIME) = range(6)

def get_fileinfo(file, pardir_flag = 0, show_dirs_size = 0):
    """return information about a file in next format:
    (filetype, perms, owner, group, size, mtime).
    """

    st = os.lstat(file)
    type = __get_filetype(file)
    if (type == FTYPE_DIR or type == FTYPE_LNK2DIR) and not pardir_flag \
       and show_dirs_size:
        size = __get_size(file)
    elif type == FTYPE_CDEV or type == FTYPE_BDEV:
        # HACK: it's too time consuming to calculate all files' rdevs
        #       in a directory, so we just calculate needed ones
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
    return (type, stat.S_IMODE(st[stat.ST_MODE]), owner, group,
            size, st[stat.ST_MTIME])


def get_dir(path):
    """return a dict whose elements are formed by file name as key
    and a (filetype, perms, owner, group, size, mtime) tuple as value.
    """

    path = os.path.normpath(path)
    files_dict = {}
    if path != os.sep:
        files_dict[os.pardir] = get_fileinfo(os.path.dirname(path), 1)
    files_list = os.listdir(path)
    for file in files_list:
        files_dict[file] = get_fileinfo(os.path.join(path, file))
    return len(files_dict), files_dict


########################################################################
########################################################################
# Sort Type:    None, byName, bySize, byDate, byType
(SORTTYPE_None, SORTTYPE_byName, SORTTYPE_byName_rev, SORTTYPE_bySize,
 SORTTYPE_bySize_rev, SORTTYPE_byDate, SORTTYPE_byDate_rev) = range(7)

def __do_sort(f_dict, sortmode, sort_mix_cases):
    if sortmode == SORTTYPE_None:
        names = f_dict.keys()
        if names.count(os.pardir):
            names.remove(os.pardir)
            names.insert(0, os.pardir)
        return names

    if sortmode == SORTTYPE_byName or sortmode == SORTTYPE_byName_rev:
        if sort_mix_cases:
            names2 = [n.lower() for n in f_dict.keys()]
            names2.sort()
            names = []
            for n in names2:
                for f in f_dict.keys():
                    if f.lower() == n:
                        try:
                            names.index(f)
                        except:
                            names.append(f)
                        continue
        else:
            names = f_dict.keys()
            names.sort()
        if sortmode == SORTTYPE_byName_rev:
            names.reverse()
        if names.count(os.pardir):
            names.remove(os.pardir)
            names.insert(0, os.pardir)
        return names

    dict = {}
    for k in f_dict.keys():
        if sortmode == SORTTYPE_bySize or sortmode == SORTTYPE_bySize_rev:
            size = f_dict[k][FT_SIZE]
            while dict.has_key(size):    # can't be 2 entries with same key
                size += 0.1
            dict[size] = k
        elif sortmode == SORTTYPE_byDate or sortmode == SORTTYPE_byDate_rev:
            time = f_dict[k][FT_MTIME]
            while dict.has_key(time):    # can't be 2 entries with same key
                time += 0.1
            dict[time] = k
        else:
            raise ValueError

    values = dict.keys()
    values.sort()
    names = []
    for v in values:
        names.append(dict[v])
    if sortmode == SORTTYPE_bySize_rev or sortmode == SORTTYPE_byDate_rev:
        names.reverse()
    if names.count(os.pardir):
        names.remove(os.pardir)
        names.insert(0, os.pardir)
    return names

    
def sort_dir(files_dict, sortmode, sort_mix_dirs, sort_mix_cases):
    """return an array of files which are sorted by mode
    """

    # divide directories and files
    d = {}
    f = {}
    if sort_mix_dirs:
        f = files_dict
    else:
        for k, v in files_dict.items():
            if v[FT_TYPE] == FTYPE_DIR or v[FT_TYPE] == FTYPE_LNK2DIR:
                d[k] = v
            else:
                f[k] = v

    # sort
    d1 = __do_sort(d, sortmode, sort_mix_cases)
    d2 = __do_sort(f, sortmode, sort_mix_cases)
    d1.extend(d2)
    return d1
                

########################################################################
########################################################################
def get_fileinfostr(path, filename, filevalues):
    type = filevalues[FT_TYPE]
    type_chr = FILETYPES[type][0]
    if len(filename) > 21:
        fname = filename[:12] + '~' + filename[-8:]
    else:
        fname = filename
    perms = perms2str(filevalues[1])
    if -15552000 < (time.time() - filevalues[FT_MTIME]) < 15552000:
        # filedate < 6 months from now, past or future
        mtime = time.strftime('%a %b %d %H:%M', time.localtime(filevalues[FT_MTIME]))
    else:
        mtime = time.strftime('%a  %d %b %Y', time.localtime(filevalues[FT_MTIME]))
    if type == FTYPE_CDEV or type == FTYPE_BDEV:
        # HACK: it's too time consuming to calculate all files' rdevs
        #       in a directory, so we just calculate needed ones here
        #       at show time
        maj_rdev, min_rdev = get_rdev(os.path.join(path, filename))
        buf = '%c%-21s   %3d,%3d %-8s %-8s%11s%18s' % (type_chr, fname,
                                                       maj_rdev, min_rdev,
                                                       filevalues[FT_OWNER],
                                                       filevalues[FT_GROUP],
                                                       perms, mtime)
    else:
        buf = '%c%-21s%10d %-8s %-8s%11s%18s' % (type_chr, fname,
                                                 filevalues[FT_SIZE],
                                                 filevalues[FT_OWNER],
                                                 filevalues[FT_GROUP],
                                                 perms, mtime)
    return buf


def get_fileinfostr_short(path, filename, filevalues):
    type = filevalues[FT_TYPE]
    type_chr = FILETYPES[type][0]
    if len(filename) > 16:
        fname = filename[:9] + '~' + filename[-6:]
    else:
        fname = filename
    if -15552000 < (time.time() - filevalues[FT_MTIME]) < 15552000:
        # filedate < 6 months from now, past or future
        mtime = time.strftime('%d %b %H:%M', time.localtime(filevalues[FT_MTIME]))
    else:
        mtime = time.strftime('%d %b  %Y', time.localtime(filevalues[FT_MTIME]))
    if type == FTYPE_CDEV or type == FTYPE_BDEV:
        # HACK: it's too time consuming to calculate all files' rdevs
        #       in a directory, so we just calculate needed ones here
        #       at show time
        maj_rdev, min_rdev = get_rdev(os.path.join(path, filename))
        buf = '%c%-16s %3d,%3d %12s' % (type_chr, fname,
                                          maj_rdev, min_rdev, mtime)
    else:
        size = filevalues[FT_SIZE]
        if size >= 10000000000L:
            size = str(size/(1024*1024)) + 'G'            
        elif size >= 10000000L:
            size = str(size/1024) + 'K'
        else:
            size = str(size)
        buf = '%c%-16s %7s %12s' % (type_chr, fname, size, mtime)
    return buf


def perms2str(p):
    permis = ['x', 'w', 'r']
    perms = ['-'] * 9
    for i in range(9):
        if p & (0400 >> i):
            perms[i] = permis[(8-i) % 3]
    if p & 04000:
        perms[2] = 's'
    if p & 02000:
        perms[5] = 's'
    if p & 01000:
        perms[8] = 't'
    return "".join(perms)


########################################################################
########################################################################
# complete
def complete(entrypath, panelpath):
    if not entrypath:
        path = panelpath
    elif entrypath[0] == os.sep:
        path = entrypath
    else:
        path = os.path.join(panelpath, entrypath)

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
        fs = []
        for f in entries:
            if f.find(start, 0) == 0:
                fs.append(f)
        
    # sort files with dirs. first
    d1 = []
    d2 = []
    for f in fs:
        ff = os.path.join(basedir, f)
        if os.path.isdir(ff):
            d1.append(f + os.sep)
        else:
            d2.append(f)
    d1.sort()
    d2.sort()
    d1.extend(d2)
    return d1


########################################################################
########################################################################
# actions

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
        do_create_link(os.readlink(source), dest)
    elif os.path.isdir(source):
        shutil.copytree(source, dest, 1)
    elif source == dest:
        raise IOError, (0, "Source and destination are the same file")
    else:
        shutil.copy2(source, dest)


def copy(path, file, destdir, check_fileexists = 1):
    """ copy file / dir to destdir"""

    fullpath = os.path.join(path, file)
    if destdir[0] != os.sep:
        destdir = os.path.join(path, destdir)
    if os.path.isdir(destdir):
        fulldestdir = os.path.join(destdir, file)
        if os.path.exists(fulldestdir) and check_fileexists:
            return os.path.basename(fulldestdir)
    else:
        if os.path.exists(destdir) and check_fileexists:
            return os.path.basename(destdir)
        fulldestdir = destdir
    try:
        do_copy(fullpath, fulldestdir)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


# move
def move(path, file, destdir, check_fileexists = 1):
    """delete file / dir"""

    fullpath = os.path.join(path, file)
    if destdir[0] != os.sep:
        destdir = os.path.join(path, destdir)
    if os.path.isdir(destdir):
        fulldestdir = os.path.join(destdir, file)
        if os.path.exists(fulldestdir) and check_fileexists:
            return os.path.basename(fulldestdir)
    else:
        if os.path.exists(destdir) and check_fileexists:
            return os.path.basename(destdir)
        fulldestdir = destdir
    try:
        do_copy(fullpath, fulldestdir)
    except (IOError, os.error), (errno, strerror):
        do_delete(fulldestdir)
        return (strerror, errno)
    else:
        try:
            do_delete(fullpath)
        except (IOError, os.error), (errno, strerror):
            return (strerror, errno)


# delete
def do_delete(file):
    if os.path.islink(file):
        os.unlink(file)
    elif os.path.isdir(file):
        for f in os.listdir(file):
            do_delete(os.path.join(file, f))
        os.rmdir(file)
    else:
        os.unlink(file)


def delete(path, file):
    """delete file / dir"""

    fullpath = os.path.join(path, file)
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


# find/grep
def findgrep(path, files, pattern, find, egrep, ignorecase = 0):
    if ignorecase:
        ign = 'i'
    else:
        ign = ''

#      # 2>/dev/null only work in bash-type shells
#      cmd = '%s %s -name \"%s\" -print -exec %s -n%s \"%s\" {} \\; 2>/dev/null' % \
#            (find, path, files, egrep, ign, pattern)
#      try:
#          c = os.popen(cmd, 'r')
#      except:
#          return -1

#      quit = 0
#      matches = []
#      filename = ''
#      while not quit:
#          buf = c.readline()
#          if buf == '':
#              quit = 1
#          if buf.find(':') == -1:
#              filename = buf[:-1]
#          else:
#              try:
#                  nline = int(buf.split(':')[0])
#              except ValueError:
#                  filename = buf[:-1]
#              else:
#                  filename = filename.replace(path, '')
#                  if filename[0] == os.sep and path != os.sep:
#                      filename = filename[1:]        
#                  matches.append('%d:%s' % (nline, filename))
#      c.close()

    cmd = '%s %s -name \"%s\" -print' % (find, path, files)
    try:
        i, o, e = os.popen3(cmd, 'r')
    except:
        return -1
    i.close; e.close()
    fs =  [l[:-1] for l in o.readlines()]
    o.close()
    fs = [l for l in fs if not os.path.isdir(l)]
    matches = []
    for f in fs:
        try:
            buf = os.popen('%s -n%s \"%s\" \"%s\"' % (egrep, ign, pattern,
                                                      f)).readlines()
        except:
            return -1
        if not buf:
            continue
        for l in buf:
            try:
                nline = int(l.split(':')[0])
            except ValueError:
                nline = 0
            f = f.replace(path, '')
            if f[0] == os.sep and path != os.sep:
                f = f[1:]        
            matches.append('%d:%s' % (nline,f))

    return matches


def find(path, files, find):
    cmd = '%s %s -name \"%s\" -print;' % (find, path, files)
    try:
        i, c, e = os.popen3(cmd, 'r')
    except:
        return -1

    i.close; e.close()
    quit = 0
    matches = []
    filename = ''
    while not quit:
        buf = c.readline()
        if buf == '':
            quit = 1
        filename = buf[:-1]
        filename = filename.replace(path, '')
        if filename != None and filename != '':
            if filename[0] == os.sep and path != os.sep:
                filename = filename[1:]
            matches.append(filename)
    c.close()
    return matches


########################################################################
########################################################################
# utilities

def get_owners():
    """get a list with the users defined in the system"""

    owners = [e[0] for e in pwd.getpwall()]
    return owners


def get_user_fullname(user):
    """return the fullname of an user"""

    try:
        return pwd.getpwnam(user)[4]
    except KeyError:
        return '<unknown user name>'
    
    
def get_groups():
    """get a list with the groups defined in the system"""
    
    groups = [e[0] for e in grp.getgrall()]
    return groups


def set_perms(file, perms):
    """set permissions to a file"""

    ps = 0
    i = 8
    for p in perms:
        if p == 'x':
            ps += 1 * 8 ** (i / 3)
        elif p == 'w':
            ps += 2 * 8 ** (i / 3)
        elif p == 'r':
            ps += 4 * 8 ** (i / 3)
        elif p == 't' and i == 0:
            ps += 1 * 8 ** 3
        elif p == 's' and (i == 6 or i == 3):
            if i == 6:
                ps += 4 * 8 ** 3
            else:
                ps += 2 * 8 ** 3
        i -= 1
    try:
        os.chmod(file, ps)
    except (IOError, os.error), (errno, strerror):
        return (strerror, errno)


def set_owner_group(file, owner, group):
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
        os.chown(file, owner_n, group_n)
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
            if l[0] != os.sep:
                continue
            e = l.split()
            e[0] = e[0]
            e[1] = str(int(e[1]) / 1024)
            e[2] = str(int(e[2]) / 1024)
            e[3] = str(int(e[3]) / 1024)
            e[4] = e[4]
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
            fsdev = f[0]
            for e in es:
                if len(e) < 5:
                    continue
                if fsdev == e.split()[0]:
                    f.append(e.split()[fstype_pos])
                    break
            else:
                f.append('unknown')
        return fs



