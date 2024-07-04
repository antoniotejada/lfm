# -*- coding: utf-8 -*-

"""utils.py

This module contains useful functions.
"""


import os
import os.path
import time
import signal
import popen2
import select
import cPickle
import curses

import files
import compress
import messages
from __init__ import sysprogs, g_encoding


######################################################################
##### module variables
app = None


######################################################################
##### InterProcess Communication
class IPC:
    def __init__(self):
        pipe_r, pipe_w = os.pipe()
        self.rfd = os.fdopen(pipe_r, 'rb', 0)
        self.wfd = os.fdopen(pipe_w, 'wb', 0)

    def send(self, buf):
        cPickle.dump(buf, self.wfd)
        time.sleep(0.01)
        cPickle.dump(None, self.wfd)

    def receive(self):
        ready = select.select([self.rfd], [], [], 0.01)
        if self.rfd in ready[0]:
            try:
                buf = cPickle.load(self.rfd)
            except:
                return -1, 'Error unmarshaling'
            if buf == None:
                return 0, None
            try:
                arg1, arg2 = buf
            except:
                return -1, 'Malformed response'
            return 1, buf
        return 0, None

    def close(self):
        self.rfd.close()
        self.wfd.close()


######################################################################
##### Process Base Loop
class ProcessBaseLoop:
    """Run a function in background, so it can be stopped, continued, etc.
    There is also a graphical animation to show the program still runs and
    has not crashed.
    Parameters:
        action: action to perform, used in messages
        func: function to run
        lst: list of files to iterate on
        *args: arguments to pass to the function"""

    anim_char = ('|', '/', '-', '\\')

    def __init__(self, action = '', func = None, lst = [], *args):
        self.action = action
        self.func = func
        self.lst = lst
        self.args = args
        self.subtitle = ''
        self.ret = []
        self.cursor_i = 0
        self.file_i = 0
        self.filename = ''
        self.length = len(lst)
        self.init_gui()

    def init_gui(self):
        self.cur_win = curses.newpad(1, 2)
        self.cur_win.bkgd(curses.color_pair(1))
        self.dlg = messages.FixSizeProgressBarWindow('', '', '', 0,
            curses.color_pair(1), curses.color_pair(1),
            curses.color_pair(7) | curses.A_BOLD, curses.color_pair(4),
            waitkey = 0)
        self.dlg.pwin.window().nodelay(1)

    def end_gui(self):
        self.dlg.pwin.window().nodelay(0)
        self.show_parent()

    def show_parent(self):
        # FIXME: this doesn't seem to work...
#         if not self.dlg.pwin.hidden():
#             self.dlg.pwin.hide()
#         app.lpane.win.refresh()
#         app.rpane.win.refresh()
#         app.statusbar.win.refresh()
        app.display()

    def show_win(self):
        if self.dlg.pwin.hidden():
            self.dlg.pwin.show()
        title = self.action + ' %d/%d' % (self.file_i+1, self.length)
        percent = 100 * (self.file_i+1) / self.length
        self.dlg.show(title, self.filename, 'Press Ctrl-C to stop', percent)

    def animate_cursor(self):
        self.cur_win.erase()
        self.cur_win.addch(ProcessBaseLoop.anim_char[self.cursor_i%4],
                           curses.color_pair(1) | curses.A_BOLD)
        self.cur_win.refresh(0, 0, 0, app.maxw-2, 1, app.maxw-1)
        self.cursor_i += 1
        if self.cursor_i > 3:
            self.cursor_i = 0

    def check_keys(self):
        ch = self.dlg.pwin.window().getch()
        if ch == 0x03:
            os.kill(self.pid_child, signal.SIGSTOP)
            self.show_parent()
            ans = messages.confirm('Stop process',
                                   'Stop \"%s\"' % self.action.lower(), 1)
            if ans:
                os.kill(self.pid_child, signal.SIGKILL)
                os.wait()
                return -100
            else:
                os.kill(self.pid_child, signal.SIGCONT)
                return 1
        return 0

    def wait_for_answer(self):
        while True:
            # feedback from user
            status = self.check_keys()
            if status == -100: # stopped and ended by user
                return ('stopped_by_user', None)
            elif status == 1: # stopped and continued by user
                self.show_win()
            self.animate_cursor()
            # check response
            code, buf = self.c2p.receive()
            if code == 1:
                return buf
            elif code == -1:
                return ('internal_error', buf)
            else:
                continue

    def ask_confirmation(self):
        # Virtual method
        raise NotImplementedError

    def prepare_args(self):
        # Virtual method
        raise NotImplementedError

    def process_response(self, result):
        # Virtual method
        raise NotImplementedError

    def exec_file(self, args):
        # update progress dialog
        self.show_win()
        # send data to child
        self.p2c.send(('exec', args))
        # wait for answer and process it
        ans, result = self.wait_for_answer()
        if ans == 'stopped_by_user':
            return -1
        elif ans == 'internal_error':
            self.show_parent()
            messages.error(self.action, 'Parent: Internal Error: ' + result)
            return 0
        elif ans == 'error':
            self.show_parent()
            messages.error(self.action, 'Parent: Error: ' + result)
            return 0
        elif ans == 'result':
            return self.process_response(result)
        else:
            self.show_parent()
            messages.error(self.action, 'Parent: Bad response from child')
            return 0

    def return_data(self):
        return self.ret

    def run(self):
        self.p2c = IPC()
        self.c2p = IPC()
        self.pid_child = os.fork()
        if self.pid_child < 0: # error
            messages.error(self.action, 'Can\'t run function')
            return
        elif self.pid_child == 0: # child
            self.child_process()
            os._exit(0)
        # parent
        for self.file_i, self.filename in enumerate(self.lst):
            ret = self.ask_confirmation()
            if ret == -1:
                break
            elif ret == 0:
                continue
            args = self.prepare_args()
            ret = self.exec_file(args)
            if ret == -1:
                break
        # finish
        self.p2c.send(('quit', None))
        self.p2c.close()
        self.c2p.close()
        try:
            os.wait()
        except OSError:
            pass
        self.end_gui()
        return self.return_data()

    def child_process(self):
        while True:
            # wait for command to execute
            while True:
                code, buf = self.p2c.receive()
                if code == 1:
                    break
                elif code == -1:
                    self.c2p.send(('error', 'Child: ' + buf))
                    continue
                else:
                    continue
            cmd, args = buf
            # check command
            if cmd == 'quit':
                break
            elif cmd == 'exec':
                res = self.func(*args)
                self.c2p.send(('result', res))
                continue
            else:
                result = ('error', 'Child: Bad command from parent')
                self.c2p.send(('result', result))
                continue
        # end
        time.sleep(.25) # time to let parent get return value
        os._exit(0)


######################################################################
class ProcessDirSizeLoop(ProcessBaseLoop):

    def ask_confirmation(self):
        return 1

    def prepare_args(self):
        return (self.filename, ) + self.args

    def process_response(self, result):
        self.ret.append(result)
        return 0


######################################################################
class ProcessUnCompressLoop(ProcessBaseLoop):

    def ask_confirmation(self):
        return 1

    def prepare_args(self):
        return (self.filename, ) + self.args

    def process_response(self, result):
        if type(result) == type((1, )): # error
            st, msg = result
            if st == -1:
                self.show_parent()
                messages.error(self.action, msg)
        return 0


######################################################################
class ProcessCopyMoveLoop(ProcessBaseLoop):

    def __init__(self, action = '', func = None, lst = [], *args):
        ProcessBaseLoop.__init__(self, action, func, lst, *args)
        self.overwrite_all = not app.prefs.confirmations['overwrite']
        self.overwrite_none = False

    def ask_confirmation(self):
        return 1

    def prepare_args(self):
        if self.overwrite_all:
            return (self.filename, ) + self.args + (False, )
        else:
            return (self.filename, ) + self.args

    def process_response(self, result):
        if type(result) == type(''): # overwrite file?
            if self.overwrite_none:
                return 0
            self.show_parent()
            ans = messages.confirm_all_none(self.action,
                                            'Overwrite \'%s\'' % result, 1)
            if ans == -1:
                return -1
            elif ans == -2:
                self.overwrite_none = True
                return 0
            elif ans == 0:
                return 0
            elif ans == 1:
                pass
            elif ans == 2:
                self.overwrite_all = True
            args = (self.filename, ) + self.args + (False, )
            return self.exec_file(args)
        elif type(result) == type((1,)): # error from child
            self.show_parent()
            messages.error('%s \'%s\'' % (self.action, self.filename),
                           '%s (%s)' % result)
            return 0
        else:
            return 0


######################################################################
class ProcessRenameLoop(ProcessBaseLoop):

    def ask_confirmation(self):
        from actions import doEntry
        buf = 'Rename \'%s\' to' % self.filename
        tabpath = app.act_pane.act_tab.path
        self.show_parent()
        newname = doEntry(tabpath, 'Rename', buf, self.filename)
        if newname:
            self.newname = newname
            return 1
        else:
            return 0

    def prepare_args(self):
        return (self.filename, ) + self.args + (self.newname, )

    def process_response(self, result):
        if type(result) == type(''): # overwrite file?
            self.show_parent()
            ans = messages.confirm(self.action,
                                   'Overwrite \'%s\'' % result, 1)
            if ans == -1:
                return -1
            elif ans == 0:
                return 0
            elif ans == 1:
                args = (self.filename, ) + self.args + (self.newname, False)
                self.dlg.pwin.show()
                return self.exec_file(args)
        elif type(result) == type((1,)): # error from child
            self.show_parent()
            messages.error('%s \'%s\'' % (self.action, self.filename),
                           '%s (%s)' % result)
            return 0
        else:
            return 0


######################################################################
class ProcessDeleteLoop(ProcessBaseLoop):

    def __init__(self, action = '', func = None, lst = [], *args):
        ProcessBaseLoop.__init__(self, action, func, lst, *args)
        self.delete_all = not app.prefs.confirmations['delete']

    def ask_confirmation(self):
        if self.delete_all:
            return 2
        buf = 'Delete \'%s\'' % self.filename
        if app.prefs.confirmations['delete']:
            self.show_parent()
            ans = messages.confirm_all('Delete', buf, 1)
            if ans == -1:
                return -1
            elif ans == 0:
                return 0
            elif ans == 1:
                return 1
            elif ans == 2:
                self.delete_all = True
                return 2

    def prepare_args(self):
        return (self.filename, ) + self.args

    def process_response(self, result):
        if type(result) == type((1,)): # error from child
            self.show_parent()
            messages.error('%s \'%s\'' % (self.action, self.filename),
                           '%s (%s)' % result)
            return 0
        else:
            return 0


######################################################################
##### Process Func
class ProcessFunc:
    """Run a function in background, so it can be stopped, continued, etc.
    There is also a graphical animation to show the program still runs and
    has not crashed.
    Parameters:
        title: title of info window
        subtitle: subtitle of info window
        func: function to run
        *args: arguments to pass to the function
    Returns:
         (status, message)"""

    anim_char = ('|', '/', '-', '\\')

    def __init__(self, title = '', subtitle = '', func = None, *args):
        self.func = func
        self.args = args
        self.title = title[:app.maxw-14]
        self.subtitle = subtitle[:app.maxw-14]
        self.init_gui()
        self.cursor_i = 0
        self.status = 0
        self.output = []
        self.ret = None

    def init_gui(self):
        self.cur_win = curses.newpad(1, 2)
        self.cur_win.bkgd(curses.color_pair(1))
        app.statusbar.win.nodelay(1)
        self.show_parent()
        self.show_win()

    def end_gui(self):
        app.statusbar.win.nodelay(0)
        self.show_parent()

    def show_parent(self):
        # FIXME: this doesn't seem to work...
#         if not self.dlg.pwin.hidden():
#             self.dlg.pwin.hide()
#         app.lpane.win.refresh()
#         app.rpane.win.refresh()
#         app.statusbar.win.refresh()
        app.display()

    def show_win(self):
        messages.win_nokey(self.title, self.subtitle, 'Press Ctrl-C to stop')

    def animate_cursor(self):
        self.cur_win.erase()
        self.cur_win.addch(ProcessFunc.anim_char[self.cursor_i%4],
                           curses.color_pair(1) | curses.A_BOLD)
        self.cur_win.refresh(0, 0, 0, app.maxw-2, 1, app.maxw-1)
        self.cursor_i += 1
        if self.cursor_i > 3:
            self.cursor_i = 0

    def check_finish(self):
        (pid, status) = os.waitpid(self.pid_child, os.WNOHANG)
        if pid > 0:
            self.status = status >> 8
            return True
        else:
            return False

    def process_result(self):
        code, buf = self.c2p.receive()
        if code == 1:
            self.ret = buf
        elif code == -1:
            self.show_parent()
            messages.error(self.action, 'Parent: ' + buf)
            self.show_parent()
            self.show_win()
        else:
            pass

    def check_keys(self):
        ch = app.statusbar.win.getch()
        if ch == 0x03:
            os.kill(self.pid_child, signal.SIGSTOP)
            self.show_parent()
            ans = messages.confirm('Stop process',
                                   '%s %s' % (self.title, self.subtitle),
                                   1)
            if ans:
                os.kill(self.pid_child, signal.SIGKILL)
                os.wait()
                return -100
            else:
                self.show_win()
                os.kill(self.pid_child, signal.SIGCONT)
        return 0

    def run(self):
        self.c2p = IPC()
        self.pid_child = os.fork()
        if self.pid_child < 0: # error
            messages.error('Run func', 'Can\'t run function')
            return
        elif self.pid_child == 0: # child
            self.child_process(self.func, *self.args)
            os._exit(0)
        # parent
        status = 0
        while True:
            if self.check_finish():
                break
            self.process_result()
            status = self.check_keys()
            if status == -100: # stopped by user
                self.status = status
                break
            self.animate_cursor()
        # finish and return
        self.c2p.close()
        try:
            os.wait()
        except OSError:
            pass
        self.end_gui()
        if self.status == -100: # stopped by user
            return -100, 'Stopped by user'
        try:
            st, buf = self.ret
        except:
            st, buf = 0, None
        return st, buf

    def child_process(self, func, *args):
        res = func(*args)
        self.c2p.send(res)
        os._exit(0)


######################################################################
##### run_shell
def run_shell(cmd, path, return_output = False):
    if not cmd:
        return 0, ''
    cmd = 'cd "%s"; %s' % (path, cmd)
    p = popen2.Popen3(cmd, capturestderr=True)
    p.tochild.close()
    outfd, errfd = p.fromchild, p.childerr
    output, error = [], []
    while True:
        # check if finished
        (pid, status) = os.waitpid(p.pid, os.WNOHANG)
        if pid > 0:
            status = status >> 8
            o = p.fromchild.readline()
            while o: # get output before quit
                o = o.strip()
                if o:
                    output.append(o)
                o = p.fromchild.readline()
            e = p.childerr.readline()
            while e: # get error before quit
                e = e.strip()
                if e:
                    error.append(e)
                e = p.childerr.readline()
            break
        # check for output
        ready = select.select([outfd, errfd], [], [], .01)
        if outfd in ready[0]:
            o = p.fromchild.readline()
            if o:
                output.append(o)
        if errfd in ready[0]:
            e = p.childerr.readline()
            while e: # get the whole error message
                e = e.strip()
                if e:
                    error.append(e)
                e = p.childerr.readline()
            status = p.wait() >> 8
            break
        time.sleep(0.1) # extra time to update output in case execution is too fast
    # return
    p.fromchild.close()
    p.childerr.close()
    if status != 0:
        error.insert(0, 'Exit code: %d' % status)
        return -1, '\n'.join(error)
    if error != []:
        return -1, '\n'.join(error)
    if return_output:
        return 0, '\n'.join(output)
    else:
        return 0, ''


######################################################################
##### run_dettached
def run_dettached(prog, *args):
    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.chdir('/')
        try:
            maxfd = os.sysconf("SC_OPEN_MAX")
        except (AttributeError, ValueError):
            maxfd = 256       # default maximum
        for fd in xrange(0, maxfd):
            try:
                os.close(fd)
            except OSError:   # ERROR (ignore)
                pass
        # Redirect the standard file descriptors to /dev/null.
        os.open("/dev/null", os.O_RDONLY)     # standard input (0)
        os.open("/dev/null", os.O_RDWR)       # standard output (1)
        os.open("/dev/null", os.O_RDWR)       # standard error (2)
        pid2 = os.fork()
        if pid2 == 0:
            os.execlp(prog, prog, *args)
        else:
            os.waitpid(-1, os.P_NOWAIT)
        os._exit(0)
    else:
        os.wait()


######################################################################
##### get_shell_output
# get output from a command run in shell
def get_shell_output(cmd):
    i, a = os.popen4(cmd)
    buf = a.read()
    i.close(), a.close()
    return buf.strip()


# get output from a command run in shell, no stderr
def get_shell_output2(cmd):
    i, o, e = os.popen3(cmd)
    buf = o.read()
    i.close(), o.close(), e.close()
    if buf:
        return buf.strip()
    else:
        return ''


######################################################################
##### un/compress(ed) files
# compress/uncompress file: gzip/gunzip, bzip2/bunzip2
def do_compress_uncompress_file(filename, path, typ):
    if os.path.isabs(filename):
        fullfile = filename
        filename = os.path.basename(filename)
    else:
        fullfile = os.path.join(path, filename)
    if not os.path.isfile(fullfile):
        return -1, '%s: can\'t un/compress' % filename
    c = compress.check_compressed_file(fullfile)
    if c == None:
        packager = compress.packagers_by_type[typ]
        c = packager(fullfile)
        cmd = c.build_compress_cmd()
    elif c.type == typ:
        cmd = c.build_uncompress_cmd()
    else:
        return -1, '%s: can\'t un/compress with %s' % \
            (filename, compress.packagers_by_type[typ].compress_prog)
    st, msg = run_shell(cmd, path, return_output=True)
    return st, msg

def compress_uncompress_file(tab, typ):
    if tab.selections:
        fs = tab.selections[:]
    else:
        fs = [tab.sorted[tab.file_i]]
    ProcessUnCompressLoop('Un/Compressing file',
                          do_compress_uncompress_file,
                          fs, tab.path, typ).run()
    tab.selections = []
    app.regenerate()


# uncompress directory
def do_uncompress_dir(filename, path, dest, is_tmp = False):
    if os.path.isabs(filename):
        fullfile = filename
        filename = os.path.basename(filename)
    else:
        fullfile = os.path.join(path, filename)
    if not os.path.isfile(fullfile):
        return -1, '%s: is not a file' % filename
    c = compress.check_compressed_file(fullfile)
    if c == None:
        return -1, '%s: can\'t uncompress' % filename
    cmd = c.build_uncompress_cmd()
    st, msg = run_shell(cmd, dest, return_output=True)
    if st < 0: # (-100, -1),
        # never reached if user stops (-100) because this process is killed
        c.delete_uncompress_temp(dest, is_tmp)
    return st, msg


def uncompress_dir(tab, dest = None, is_tmp = False):
    """uncompress tarred file in path directory"""

    if dest == None:
        dest = tab.path
    if tab.selections:
        fs = tab.selections[:]
    else:
        fs = [tab.sorted[tab.file_i]]
    ProcessUnCompressLoop('Uncompressing file', do_uncompress_dir,
                          fs, tab.path, dest, is_tmp).run()
    tab.selections = []


# compress directory: tar and gzip, bzip2
def do_compress_dir(filename, path, typ, dest, is_tmp = False):
    if os.path.isabs(filename):
        fullfile = filename
        filename = os.path.basename(filename)
    else:
        fullfile = os.path.join(path, filename)
    if not os.path.isdir(fullfile):
        return -1, '%s: is not a directory' % filename
    c = compress.packagers_by_type[typ](fullfile)
    if c == None:
        return -1, '%s: can\'t compress' % filename
    cmd = c.build_compress_cmd()
    st, msg = run_shell(cmd, dest, return_output = True)
    if st < 0: # (-100, -1):
        # never reached if user stops (-100) because this process is killed
        c.delete_compress_temp(dest, is_tmp)
    return st, msg


def compress_dir(tab, typ, dest = None, is_tmp = False):
    """compress directory to current path"""

    if dest == None:
        dest = tab.path
    if tab.selections:
        fs = tab.selections[:]
    else:
        fs = [tab.sorted[tab.file_i]]
    ProcessUnCompressLoop('Compressing file', do_compress_dir,
                          fs, tab.path, typ, dest, is_tmp).run()
    tab.selections = []


######################################################################
##### find / grep
# find/grep
def do_findgrep(path, files, pattern, ignorecase = 0):
    # escape special chars
    pat_re = pattern.replace('\\', '\\\\\\\\')
    pat_re = pat_re.replace('-', '\\-')
    pat_re = pat_re.replace('(', '\\(').replace(')', '\\)')
    pat_re = pat_re.replace('[', '\\[').replace(']', '\\]')
    if ignorecase:
        ign = 'i'
    else:
        ign = ''
    # 1st. version: find . -name "*.py" -print0 | xargs --null grep -Eni PATTERN
#     cmd = '%s %s -name \"%s\" -print0 | %s --null %s -En%s %s' % \
#           (sysprogs['find'], path, files, sysprogs['xargs'],
#            sysprogs['grep'], ign, pattern)
    # 2nd. version: find . -name "*.py" -exec grep -EHni PATTERN
    cmd = '%s %s -name \"%s\" -exec %s -EHn%s \"%s\" {} \\;' % \
          (sysprogs['find'], path, files, sysprogs['grep'], ign, pat_re)
    st, ret = ProcessFunc('Searching',
                          'Searching for \"%s\" in \"%s\" files' % (pattern, files),
                          run_shell, cmd, path, True).run()
    if not ret:
        return 0, []
    if st < 0: # (-100, -1) => error
        return st, ret
    elif st == 0:
        ret = ret.split('\n')
    matches = []
    if len(ret) > 0:
        # filename:linenumber:matching
        # note that filename could contain ':', so we have to parse
        for l in ret:
            if not l:
                continue
            lst = l.split(':')
            if len(lst) == 1: # binary file
                linenumber = '0'
                filename = lst[0].split(' ')[-1]
            else:
                i = len(lst) - 2
                while True:
                    filename = ':'.join(lst[:i])
                    if os.path.exists(filename):
                        break
                    else:
                        i -= 1
                linenumber = lst[i]
            filename = filename.replace(path, '')
            if filename[0] == os.sep and path != os.sep:
                filename = filename[1:]
            matches.append('%s:%s' % (linenumber, filename))
    return 0, matches


# find
def do_find(path, files):
    cmd = '%s %s -name \"%s\" -print' % (sysprogs['find'], path, files)
    st, ret = ProcessFunc('Searching',
                          'Searching for \"%s\" files' % files,
                          run_shell, cmd, path, True).run()
    if not ret:
        return 0, []
    if st < 0: # (-100, -1) => error
        return st, ret
    elif st == 0:
        ret = ret.split()
    matches = []
    if len(ret) > 0:
        matches = []
        for filename in ret:
            filename = filename.strip().replace(path, '')
            if filename != None and filename != '':
                if filename[0] == os.sep and path != os.sep:
                    filename = filename[1:]
                matches.append(filename)
    return 0, matches


######################################################################
##### encode/decode strings
def encode(buf):
    return buf.encode(g_encoding)


def decode(buf):
    codecs_lst = (g_encoding, 'utf-8', 'latin-1', 'ascii')
    for c in codecs_lst:
        try:
            buf = buf.decode(c)
        except UnicodeDecodeError:
            continue
        else:
            return buf
    else:
        return buf.decode('ascii', 'replace')


######################################################################
##### useful functions
def get_escaped_filename(filename):
    filename = filename.replace('$', '\\$')
    if filename.find('"') != -1:
        filename = filename.replace('"', '\\"')
    return '%s' % filename


def get_escaped_command(cmd, filename):
    filename = filename.replace('$', '\$')
    if filename.find('"') != -1:
        filename = filename.replace('"', '\\"')
        return '%s \'%s\'' % (cmd, filename)
    else:
        return '%s \"%s\"' % (cmd, filename)


def run_on_current_file(program, tab):
    cmd = get_escaped_command(app.prefs.progs[program],
                              tab.get_fullpathfile())
    curses.endwin()
    os.system(cmd)
    curses.curs_set(0)


######################################################################
