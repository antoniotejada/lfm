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

    try:
        buf = os.popen('du -sb \"%s\"' % file).read()
    except:
        return 0
    else:
        return int(buf.split()[0])


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
# File Type:    dir, link to directory, link, nlink, char dev,
#               block dev, fifo, socket, executable, file
FTYPE_DIR = 0; FTYPE_LNK2DIR = 1; FTYPE_LNK = 2; FTYPE_NLNK = 3
FTYPE_CDEV = 4; FTYPE_BDEV = 5; FTYPE_FIFO = 6; FTYPE_SOCKET = 7
FTYPE_EXE = 8; FTYPE_REG = 9
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
        return FTYPE_REG
    return FTYPE_REG           # if no other type, regular file


FT_TYPE = 0; FT_PERMS = 1
FT_OWNER = 2; FT_GROUP = 3
FT_SIZE = 4; FT_MTIME = 5
def get_fileinfo(file, pardir_flag = 0, show_dirs_size = 0):
    """return information about a file in next format:
    (filetype, perms, owner, group, size, mtime).
    """

    st = os.lstat(file)
    type = __get_filetype(file)
    # FIXME: prefs size dirs... => and 0
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
SORTTYPE_None = 0
SORTTYPE_byName = 1
SORTTYPE_byName_rev = 2
SORTTYPE_bySize = 3
SORTTYPE_bySize_rev = 4
SORTTYPE_byDate = 5
SORTTYPE_byDate_rev = 6

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
    perms = __perms2str(filevalues[1])
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


def __perms2str(p):
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
def complete(path, basepath, curpath):
    if not path:
        path = curpath
    elif path[0] != os.sep:
        path = os.path.join(basepath, path)
    if os.path.isdir(path):
        basedir = path
        fs = os.listdir(path)
    else:
        basedir = os.path.dirname(path)
        start = os.path.basename(path)
        entries = os.listdir(basedir)
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



def join(directory, file):
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    return os.path.join(directory, file)


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

