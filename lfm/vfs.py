# -*- coding: utf-8 -*-

"""vfs.py

This module supplies vfs functionality.
"""

import os, os.path
from glob import glob
import files
import messages
import utils
import compress


######################################################################
##### module variables
app = None


######################################################################
##### VFS
# initialize vfs stuff
def init(tab, filename, vfstype):
    """initiliaze vfs stuff"""

    tempdir = files.mkdtemp()
    # uncompress
    st, msg = utils.ProcessFunc('Creating vfs', filename,
                                utils.do_uncompress_dir, filename,
                                tab.path, tempdir, True).run()
    if st == -1: # error
        app.display()
        messages.error('Creating vfs', msg)
        app.display()
        return # temppdir deleted by previous call, so we just return
    elif st == -100: # stopped by user
        try:
            files.do_delete(tempdir)
        except OSError:
            pass
        return
    # update vfs vars
    vpath = tab.path
    tab.init(tempdir)
    tab.vfs = vfstype
    tab.base = tempdir
    tab.vbase = os.path.join(vpath, filename) + '#vfs'
    # refresh the other panel
    app.regenerate()


# copy vfs
def copy(tab_org, tab_new):
    """copy vfs"""

    tempdir = files.mkdtemp()
    # copy contents
    dir_src = tab_org.base
    for f in glob(os.path.join(dir_src, '*')):
        f = os.path.basename(f)
        try:
            files.do_copy(os.path.join(dir_src, f), os.path.join(tempdir, f))
        except (IOError, os.error), (errno, strerror):
            app.display()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))
    # init vars
    tab_new.base = tempdir
    tab_new.vfs = tab_org.vfs
    tab_new.vbase = tab_org.vbase


# exit from vfs, clean all
def exit(tab):
    """exit from vfs, clean all"""

    ans = 0
    rebuild = app.prefs.options['rebuild_vfs']
    if app.prefs.confirmations['ask_rebuild_vfs']:
        ans = messages.confirm('Rebuild vfs file', 'Rebuild vfs file', rebuild)
        app.display()
    if ans:
        if tab.vfs == 'pan':
            return pan_regenerate(tab)
        else:
            regenerate_file(tab)

    files.do_delete(tab.base)
    app.regenerate()


# regenerate vfs file
def regenerate_file(tab):
    """regenerate vfs file: compress new file"""

    vfs_file = tab.vbase.replace('#vfs', '')
    # compress file
    tmpfile = files.mktemp()
    c = compress.check_compressed_file(vfs_file)
    cmd = c.build_compressXXX_cmd('*', tmpfile)
    f = os.path.basename(vfs_file)
    st, buf = utils.ProcessFunc('Compressing Directory', '\'%s\'' % f,
                                utils.run_shell, cmd, tab.base).run()
    if st == -1: # error
        app.display()
        messages.error('Creating vfs', buf)
        app.display()
        try:
            files.do_delete(tmpfile)
        except OSError:
            pass
    elif st == -100: # stopped by user
        try:
            files.do_delete(tmpfile)
        except OSError:
            pass
    else:
        tmpfile += c.exts[0] # zip & rar always adds extension
        # copy file
        try:
            files.do_copy(tmpfile, vfs_file)
        except (IOError, os.error), (errno, strerror):
            files.do_delete(tmpfile)
            return '%s (%s)' % (strerror, errno)
        files.do_delete(tmpfile)


# vfs path join
def join(tab):
    if tab.base == tab.path:
        return tab.vbase
    else:
        return tab.vbase + tab.path.replace(tab.base, '')


# initialize panelize vfs stuff
def pan_init(tab, fs):
    """initiliaze panelize vfs stuff"""

    vfstype = 'pan'
    tempdir = files.mkdtemp()
    # copy files
    for f in fs:
        f_orig = os.path.join(tab.path, f)
        f_dest = os.path.join(tempdir, f)
        d = os.path.join(tempdir, os.path.dirname(f))
        try:
            os.makedirs(d)
        except (IOError, os.error), (errno, strerror):
            pass
        try:
            if os.path.isfile(f_orig):
                files.do_copy(f_orig, f_dest)
            elif os.path.isdir(f_orig):
                os.mkdir(f_dest)
        except (IOError, os.error), (errno, strerror):
            messages.error('Can\'t create vfs', '%s (%s)' % (strerror, errno))
    # update vfs vars
    vpath = tab.path
    tab.init(tempdir)
    tab.vfs = vfstype
    tab.base = tempdir
    tab.vbase = vpath + '#vfs'


# copy pan vfs
def pan_copy(tab_org, tab_new):
    """copy vfs"""

    tempdir = files.mkdtemp()
    # copy contents
    dir_src = tab_org.base
    for f in glob(os.path.join(dir_src, '*')):
        f = os.path.basename(f)
        try:
            files.do_copy(os.path.join(dir_src, f), os.path.join(tempdir, f))
        except (IOError, os.error), (errno, strerror):
            app.display()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))
    # init vars
    tab_new.base = tempdir
    tab_new.vfs = tab_org.vfs
    tab_new.vbase = tab_org.vbase


# regenerate vfs pan file
def pan_regenerate(tab):
    """regenerate vfs pan file: copy files"""

    dir_src = tab.path
    dir_dest = tab.vbase.replace('#vfs', '')
    # check if can copy files
    i, oe = os.popen4('touch ' + dir_dest, 'r')
    out = oe.read()
    i.close(), oe.close()
    if out:
        return ''.join(out.split(':')[1:])[1:]
    # copy files
    for f in glob(os.path.join(dir_src, '*')):
        f = os.path.basename(f)
        try:
            files.do_copy(os.path.join(dir_src, f), os.path.join(dir_dest, f))
        except (IOError, os.error), (errno, strerror):
            app.display()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))


######################################################################
