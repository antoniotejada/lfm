# -*- coding: iso-8859-15 -*-

"""vfs.py

This module supplies vfs functionality.
"""

import os, os.path
from glob import glob
import files
import messages
from utils import run_thread, do_uncompress_dir


##################################################
##### VFS
##################################################
# initialize vfs stuff
def init(app, panel, filename, vfstype):
    """initiliaze vfs stuff"""

    # check tar exists
    if not vfstype.endswith('unzip'):
        if app.prefs.progs['tar'] == '':
            messages.error('Uncompress directory', 'No tar program found in path')
            return
    # create temp. dir
    tempdir = files.mktemp()
    try:
        os.mkdir(tempdir, 0700)
    except (IOError, os.error), (errno, strerror):
        messages.error('Can\'t create vfs for \'%s\'' % filename,
                       '%s (%s)' % (strerror, errno))
        return
    # uncompress
    err = run_thread(app, 'Creating vfs for \'%s\'' % filename, do_uncompress_dir,
                     app, panel.path, vfstype, filename, tempdir)
    if err and err != -100:
        messages.error('Error uncompressing \'%s\'' % filename, err)
        return
    # update vfs vars
    vpath = panel.path
    panel.init_dir(tempdir)
    panel.fix_limits()
    panel.vfs = vfstype
    panel.base = tempdir
    panel.vbase = os.path.join(vpath, filename) + '#vfs'
    # refresh the other panel
    panel.refresh_panel(app.get_otherpanel())


# copy vfs
def copy(app, panel_org, panel_new):
    """copy vfs"""

    # create temp. dir
    tempdir = files.mktemp()
    try:
        os.mkdir(tempdir, 0700)
    except (IOError, os.error), (errno, strerror):
        messages.error('Can\'t create vfs for \'%s\'' % filename,
                       '%s (%s)' % (strerror, errno))
        return
    # copy contents
    dir_src = panel_org.base
    for f in glob(os.path.join(dir_src, '*')):
        f = os.path.basename(f)
        try:
            files.do_copy(os.path.join(dir_src, f), os.path.join(tempdir, f))
        except (IOError, os.error), (errno, strerror):
            app.show()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))
    # init vars
    panel_new.base = tempdir
    panel_new.vfs = panel_org.vfs
    panel_new.vbase = panel_org.vbase


# exit from vfs, clean all
def exit(app, panel):
    """exit from vfs, clean all"""

    rebuild = app.prefs.options['rebuild_vfs']
    if app.prefs.confirmations['ask_rebuild_vfs']:
        ans = messages.confirm('Rebuild vfs file', 'Rebuild vfs file', rebuild)
        app.show()
    if ans:
        err = run_thread(app, 'Regenerating vfs file', regenerate_file,
                         app, panel)
        if err and err != -100:
            app.show()
            messages.error('Error regenerating vfs file', err)
    files.do_delete(panel.base)
    panel.refresh_panel(app.get_otherpanel())
    panel.refresh_panel(panel)


# regenerate vfs file
def regenerate_file(app, panel):
    """regenerate vfs file: compress new file"""

    if panel.vfs == 'pan':
        return pan_regenerate(app, panel)
    # check if can regenerate vfs file
    vfs_file = panel.vbase.replace('#vfs', '')
    i, oe = os.popen4('touch ' + vfs_file, 'r')
    out = oe.read()
    i.close(), oe.close()
    if out:
        return ''.join(out.split(':')[1:])[1:]
    # compress file
    mask = os.umask(0066)
    tmpfile = files.mktemp()
    prog = os.path.basename(panel.vfs)
    if prog == 'unzip':
        prog = 'zip'
        tmpfile += '.zip'
        i, oe = os.popen4('cd \"%s\"; %s -rq \"%s\" %s; echo ZZENDZZ' %
                          (panel.base, app.prefs.progs[prog], tmpfile, '*'))
    else:
        i, oe = os.popen4('cd \"%s\"; %s cf - %s | %s >%s; echo ZZENDZZ' %
                          (panel.base, app.prefs.progs['tar'],
                           '*', app.prefs.progs[prog], tmpfile))
    while 1:
        buf = oe.read()[:-1]
        if buf == 'ZZENDZZ':
            break
        else:
            i.close(); oe.close()
            buf = buf.replace('ZZENDZZ', '')
            return (buf, '')
        i.close(); oe.close()
    os.umask(mask)
    # copy file
    try:
        files.do_copy(tmpfile, vfs_file)
    except (IOError, os.error), (errno, strerror):
        os.unlink(tmpfile)
        return '%s (%s)' % (strerror, errno)
    os.unlink(tmpfile)


# vfs path join
def join(app, panel):
    if panel.base == panel.path:
        return panel.vbase
    else:
        return panel.vbase + panel.path.replace(panel.base, '')


# initialize panelize vfs stuff
def pan_init(app, panel, fs):
    """initiliaze panelize vfs stuff"""

    vfstype = 'pan'
    # create temp. dir
    tempdir = files.mktemp()
    try:
        os.mkdir(tempdir, 0700)
    except (IOError, os.error), (errno, strerror):
        messages.error('Can\'t create vfs for \'%s\'' % filename,
                       '%s (%s)' % (strerror, errno))
        return
    # copy files
    for f in fs:
        f_orig = os.path.join(panel.path, f)
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
            messages.error('Can\'t create vfs for \'%s\'' % f,
                           '%s (%s)' % (strerror, errno))
    # update vfs vars
    vpath = panel.path
    panel.init_dir(tempdir)
    panel.fix_limits()
    panel.vfs = vfstype
    panel.base = tempdir
    panel.vbase = vpath + '#vfs'
    

# copy pan vfs
def pan_copy(app, panel_org, panel_new):
    """copy vfs"""

    # create temp. dir
    tempdir = files.mktemp()
    try:
        os.mkdir(tempdir, 0700)
    except (IOError, os.error), (errno, strerror):
        messages.error('Can\'t create vfs for \'%s\'' % filename,
                       '%s (%s)' % (strerror, errno))
        return
    # copy contents
    dir_src = panel_org.base
    for f in glob(os.path.join(dir_src, '*')):
        f = os.path.basename(f)
        try:
            files.do_copy(os.path.join(dir_src, f), os.path.join(tempdir, f))
        except (IOError, os.error), (errno, strerror):
            app.show()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))
    # init vars
    panel_new.base = tempdir
    panel_new.vfs = panel_org.vfs
    panel_new.vbase = panel_org.vbase


# regenerate vfs pan file
def pan_regenerate(app, panel):
    """regenerate vfs pan file: copy files"""

    dir_src = panel.path
    dir_dest = panel.vbase.replace('#vfs', '')
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
            app.show()
            messages.error('Error regenerating vfs file',
                           '%s (%s)' % (strerror, errno))
