# -*- coding: iso-8859-15 -*-

"""utils.py

This module contains useful functions.
"""


import os
import time, signal, cPickle
import curses
import files
import messages


##################################################
##### run_thread
##################################################
# run thread: return -100 if stopped
def run_thread(app, title = 'Doing nothing', func = None, *args):
    """Run a function in background, so it can be stopped, continued, etc.
    There is also a graphical ad to show the program still runs and is not
    crashed. Returns nothing if all was ok, -100 if stoppped by user, or
    an error message."""

    title = title[:curses.COLS-14]
    app.show()
    messages.win_nokey(title, title, 'Press Ctrl-C to stop')
    app.win_title.nodelay(1)
    filename = files.mktemp()
    pid = os.getpid()
    thread_pid = os.fork()
    # error
    if thread_pid < 0:
        messages.error('Run Process', 'Can\'t execute process')
        return
    # child
    elif thread_pid == 0:
        res = func(*args)
        mask = os.umask(0066)
        file = open(filename, 'w')
        cPickle.dump(res, file)
        file.close()
        os.umask(mask)
        os._exit(0)
    # parent
    while 1:
        (th_pid, status) = os.waitpid(thread_pid, os.WNOHANG)
        if th_pid > 0:
            break
        ch = app.win_title.getch()
        if ch == 0x03:
            os.kill(thread_pid, signal.SIGSTOP)
            for panel in app.panels:
                panel.show()
            ans = messages.confirm('Stop process',
                                   'Stop \"%s\"' % title.lower(), 1)
            if ans:
                os.kill(thread_pid, signal.SIGKILL)
                app.win_title.nodelay(0)
                os.wait()
                return -100
            else:
                app.show()
                messages.win_nokey(title, title + '\n\nPress Ctrl-C to stop')
                os.kill(thread_pid, signal.SIGCONT)
        app.win_title.addstr(0, curses.COLS-2, '|')
        app.win_title.refresh()
        time.sleep(0.05)
        app.win_title.addstr(0, curses.COLS-2, '/')
        app.win_title.refresh()
        time.sleep(0.05)
        app.win_title.addstr(0, curses.COLS-2, '-')
        app.win_title.refresh()
        time.sleep(0.05)
        app.win_title.addstr(0, curses.COLS-2, '\\')
        app.win_title.refresh()
        time.sleep(0.05)

    # return res
    app.win_title.nodelay(0)
    file = open(filename, 'r')
    res = cPickle.load(file)
    file.close()
    os.unlink(filename)
    return res


##################################################
##### un/compress(ed) files
##################################################
# compress/uncompress file: gzip/gunzip, bzip2/bunzip2
def do_compress_uncompress_file(comp, prog, file, fullfile):
    if prog == 'gzip':
        ext = '.gz'
    else:
        ext = '.bz2'
    if len(file) > len(ext) and file[-len(ext):] == ext:
        i, a = os.popen4('%s -d \"%s\"' % (comp, fullfile))
    else:
        i, a = os.popen4('%s \"%s\"' % (comp, fullfile))
    err = a.read()
    i.close(); a.close()
    return err


def compress_uncompress_file(app, panel, prog):
    comp = app.prefs.progs[prog]
    if comp == '':
        app.show()
        messages.error(prog, 'No %s program found in path' % prog)
        return
    if panel.selections:
        print panel.selections
        for f in panel.selections:
            fullfile = os.path.join(panel.path, f)
            if not os.path.isfile(fullfile):
                app.show()
                messages.error(comp, '%s: Can\'t un/compress' % f)
                continue
            err = run_thread(app, 'Un/Compressing \'%s\'' % f,
                             do_compress_uncompress_file,
                             comp, prog, f, fullfile)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error un/compressing \'%s\'' % f, err.strip())
                continue
        old_file = panel.file_i
        panel.init_dir(panel.path)
        panel.file_i = old_file
        old_file = app.get_otherpanel().file_i
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = old_file
    else:
        file = panel.sorted[panel.file_i]
        fullfile = os.path.join(panel.path, file)
        if not os.path.isfile(fullfile):
            app.show()
            messages.error(comp, '%s: Can\'t un/compress' % file)
            return
        err = run_thread(app, 'Un/Compressing \'%s\'' % file,
                         do_compress_uncompress_file, comp, prog, file, fullfile)
        if err and err != -100:
            for panel in app.panels:
                panel.show()
            messages.error('Error un/compressing \'%s\'' % file, err.strip())
        old_file = panel.file_i
        panel.refresh_panel(panel)
        panel.file_i = old_file
        old_file = app.get_otherpanel().file_i
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = old_file


# uncompress directory
def check_compressed_tarfile(app, file):
    """check if correct compressed (and tar-ed file), if so returns compress
    program"""

    if (len(file) > 7 and file[-7:] == '.tar.gz') or \
       (len(file) > 4 and file[-4:] == '.tgz') or \
       (len(file) > 6 and file[-6:] == '.tar.Z'):
        return app.prefs.progs['gzip']
    elif (len(file) > 8 and file[-8:] == '.tar.bz2'):
        return app.prefs.progs['bzip2']
    elif (len(file) > 4 and file[-4:] == '.zip'):
        return app.prefs.progs['unzip']
    else:
        return -1


def do_uncompress_dir(app, path, comp, file, destdir = '.'):
    if destdir == '.':
        destdir = path
    if comp.endswith('unzip'):
        i, oe = os.popen4('cd \"%s\"; %s -q \"%s\"; echo ZZENDZZ' %
                          (destdir, comp, os.path.join(path, file)))
    else:
        i, oe = os.popen4('cd \"%s\"; %s -d \"%s\" -c | %s xf -; echo ZZENDZZ' %
                          (destdir, comp, os.path.join(path, file),
                           app.prefs.progs['tar']))
    while 1:
        buf = oe.read()[:-1]
        if buf == 'ZZENDZZ':
            i.close(); oe.close()
            return
        else:
            i.close(); oe.close()
            buf = buf.replace('ZZENDZZ', '')
            return buf

    
def uncompress_dir(app, panel, destdir):
    """uncompress tarred file in path directory"""

    if app.prefs.progs['tar'] == '':
        app.show()
        messages.error('Uncompress directory', 'No tar program found in path')
        return
    if panel.selections:
        for file in panel.selections:
            comp = check_compressed_tarfile(app, file)
            if comp == -1:
                app.show()
                messages.error('Uncompress',
                               '%s: is not a valid compressed file' % file)
                continue
            elif comp == '':
                app.show()
                messages.error('Uncompress directory',
                               'No uncompress program found in path')
                return
            err = run_thread(app, 'Uncompressing file \'%s\'' % file,
                             do_uncompress_dir,
                             app, panel.path, comp, file, destdir)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error uncompressing \'%s\'' % file, err)
        panel.selections = []
    else:
        file = panel.sorted[panel.file_i]
        comp = check_compressed_tarfile(app, file)
        if comp == -1:
            app.show()
            messages.error('Uncompress',
                           '%s: is not a valid compressed file' % file)
            return
        elif comp == '':
            app.show()
            messages.error('Uncompress directory',
                           'No uncompress program found in path')
            return
        err = run_thread(app, 'Uncompressing file \'%s\'' % file,
                         do_uncompress_dir,
                         app, panel.path, comp, file, destdir)
        if err and err != -100:
            for panel in app.panels:
                panel.show()
            messages.error('Error uncompressing \'%s\'' % file, err)


# compress directory: tar and gzip, bzip2
def do_compress_dir(app, path, prog, file, ext):
    mask = os.umask(0066)
    tmpfile = files.mktemp()
    if ext == 'zip':
        tmpfile += '.zip'
        tar_ext = ''
        i, oe = os.popen4('cd \"%s\"; %s -rq \"%s\" \"%s\"; echo ZZENDZZ' %
                          (path, app.prefs.progs[prog], tmpfile, file))
    else:
        tar_ext = 'tar.'
        i, oe = os.popen4('cd \"%s\"; %s cf - \"%s\" | %s >%s; echo ZZENDZZ' %
                          (path, app.prefs.progs['tar'],
                           file, app.prefs.progs[prog], tmpfile))
    while 1:
        buf = oe.read()[:-1]
        if buf == 'ZZENDZZ':
            break
        else:
            i.close(); oe.close()
            buf = buf.replace('ZZENDZZ', '')
            os.unlink(tmpfile)
            return buf
    i.close(); oe.close()
    os.umask(mask)
    try:
        files.do_copy(tmpfile, os.path.join('%s' % path,
                                            '%s.%s%s' % (file, tar_ext, ext)))
    except (IOError, os.error), (errno, strerror):
        os.unlink(tmpfile)
        return '%s (%s)' % (strerror, errno)
    os.unlink(tmpfile)


def compress_dir(app, panel, prog):
    """compress directory to current path"""

    if app.prefs.progs[prog] == '':
        app.show()
        messages.error('Compress directory', 'No %s program found in path' % prog)
        return
    if prog in ('gzip', 'bzip2'):
        if app.prefs.progs['tar'] == '':
            app.show()
            messages.error('Compress directory', 'No tar program found in path')
            return
    if prog == 'gzip':
        ext = 'gz'
    elif prog == 'bzip2':
        ext = 'bz2'
    else:
        ext = 'zip'
    if panel.selections:
        for file in panel.selections:
            if not os.path.isdir(os.path.join(panel.path, file)):
                app.show()
                messages.error('Compress directory',
                               '%s: is not a directory' % file)
                continue

            err = run_thread(app, 'Compressing directory \'%s\'' % file,
                             do_compress_dir,
                             app, panel.path, prog, file, ext)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error compressing \'%s\'' % file, err)
        panel.selections = []
    else:
        file = panel.sorted[panel.file_i]
        if file == os.pardir:
            app.show()
            messages.error('Compress directory',
                           '%s: can\'t be compressed' % file)
            return
        if not os.path.isdir(os.path.join(panel.path, file)):
            app.show()
            messages.error('Compress directory',
                           '%s: is not a directory' % file)
            return
        err = run_thread(app, 'Compressing directory \'%s\'' % file,
                         do_compress_dir,
                         app, panel.path, prog, file, ext)
        if err and err != -100:
            for panel in app.panels:
                panel.show()
            messages.error('Error compressing \'%s\'' % file, err)
