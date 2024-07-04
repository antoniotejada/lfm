#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

# Copyright (C) 2001-4  Iñigo Serna
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.


"""
Copyright (C) 2001-4, Iñigo Serna <inigoserna@telefonica.net>.
All rights reserved.

This software has been realised under the GPL License, see the COPYING
file that comes with this package. There is NO WARRANTY.

'Last File Manager' is (tries to be) a simple 'midnight commander'-type
application for UNIX console.
"""


import os, os.path
import sys, time
import curses

from __init__ import *
import files
import actions
import vfs
import messages
import preferences
import pyview


##################################################
##### lfm
##################################################
class Lfm:
    """Main application class"""

    panels = []
    npanels = 0
    
    def __init__(self, win, paths, npanels = 2):
        self.win = win              # root window, needed for resizing
        self.npanels = npanels      # no. of panels showed
        self.panels = []            # list of panels
        self.panel = 0              # active panel
        self.initialized = 0
        # preferences
        self.prefs = preferences.Preferences(PREFSFILE, defaultprogs, filetypes)
        self.modes = self.prefs.modes
        # We need prefs now, but return code will be handled after
        # curses initalization, because we might need windows.
        ret = self.prefs.load()
        # check for valid programs
        self.prefs.check_progs(self.prefs.progs)
        # panels
        self.init_curses()
        # Ok, now we can handle error messages.
        if ret == -1:
            messages.error('Load Preferences',
                           '\'%s\' does not exist\nusing default values' %
                           PREFSFILE)
            self.prefs.save()
        elif ret == -2:
            messages.error('Load Preferences',
                           '\'%s\' seems corrupted\nusing default values' %
                           PREFSFILE)
            self.prefs.save()
        # rest of the panels initialization.
        if npanels == 2:
            self.panels.append(Panel(paths[0], 1, self))     # left panel
            self.panels.append(Panel(paths[1], 2, self))     # right panel
        else:
            self.panels.append(Panel(paths[0], 3, self))     # full panel
            self.panels.append(Panel(paths[1], 0, self))     # not shown
        self.initialized = 1


    def init_curses(self):
        """initialize curses stuff: windows, colors, ..."""

        self.maxh, self.maxw = self.win.getmaxyx()
        curses.cbreak()
        curses.raw()
        cursor_hide()

        # create top and bottom windows
        try:
            self.win_title = curses.newwin(1, 0, 0, 0)
            self.win_status = curses.newwin(1, 0, self.maxh-1, 0)
        except curses.error:
            print 'Can\'t create windows'
            sys.exit(-1)

        # colors
        if curses.has_colors():
            self.colors = self.prefs.colors

            # Translation table: color name -> curses color name.
            self.coltbl = {
                'black': curses.COLOR_BLACK,
                'blue': curses.COLOR_BLUE,
                'cyan': curses.COLOR_CYAN,
                'green': curses.COLOR_GREEN,
                'magenta': curses.COLOR_MAGENTA,
                'red': curses.COLOR_RED,
                'white': curses.COLOR_WHITE,
                'yellow': curses.COLOR_YELLOW }

            # Defaults of base objects. object, foregrounf, background
            colors = [
                ('title', 'yellow', 'blue'),
                ('files', 'white', 'black'),
                ('current_file', 'blue', 'cyan'),
                ('messages', 'magenta', 'cyan'),
                ('help', 'green', 'black'),
                ('file_info', 'red', 'black'),
                ('error_messages1', 'white', 'red'),
                ('error_messages2', 'black', 'red'),
                ('buttons', 'yellow', 'red'),
                ('selected_file', 'yellow', 'black'),
                ('current_selected_file', 'yellow', 'cyan') ]

            # Initialize every color pair with user colors or with the defaults.
            for i in range(len(colors)):
                curses.init_pair(i+1,
                    self.__set_color(self.colors[colors[i][0]][0], self.coltbl[colors[i][1]]),
                    self.__set_color(self.colors[colors[i][0]][1], self.coltbl[colors[i][2]]))

            self.win_title.attrset(curses.color_pair(1) | curses.A_BOLD)
            self.win_title.bkgdset(curses.color_pair(1))
            self.win_status.attrset(curses.color_pair(1))
            self.win_status.bkgdset(curses.color_pair(1))


    def resize(self):
        """resize windows"""

        h, w = self.win.getmaxyx()
        self.maxh, self.maxw = h, w
        if w == 0 or h == 2:
            return
        for p in self.panels:
            p.win_files.erase()
            p.win_files.refresh()
        self.win.resize(h, w)
        self.win_title.resize(1, w)
        self.win_status.resize(1, w)
        self.win_status.mvwin(h-1, 0)
        for p in self.panels:
            p.do_resize(h, w)
        self.show()


    def __set_color(self, col, defcol):
        """return curses color value if exists, otherwise return default"""
        if self.coltbl.has_key(col):
            return self.coltbl[col]
        else:
            return defcol


    def __show_bars(self):
        """show title and status bars"""
        
        self.win_title.erase()
        if self.maxw >= 60:
            title = '%s v%s   (c) %s, %s' % (LFM_NAME, VERSION, DATE, AUTHOR)
            pos = (self.maxw-len(title)) /2
            self.win_title.addstr(0, pos, title)
        self.win_title.refresh()

        self.win_status.erase()
        panel = self.panels[self.panel]
        if len(panel.selections):
            if self.maxw >= 45:
                size = 0
                for f in panel.selections:
                    size += panel.files[f][files.FT_SIZE]
                self.win_status.addstr('    %s bytes in %d files' % \
                                       (num2str(size), len(panel.selections)))
        else:
            if self.maxw >= 80:
                self.win_status.addstr('File: %4d of %-4d' % \
                                       (panel.file_i + 1, panel.nfiles))
                filename = panel.sorted[panel.file_i]
                if not panel.vfs:
                    realpath = files.get_realpath(panel.path, filename,
                                                  panel.files[filename][files.FT_TYPE])
                else:
                    realpath = os.path.join(vfs.join(app, panel), filename)
                if len(realpath) > self.maxw - 35:
                    path = '~' + realpath[-(self.maxw-37):]
                else:
                    path = realpath
                self.win_status.addstr(0, 20, 'Path: ' + path)
        if self.maxw > 10:
            try:
                self.win_status.addstr(0, self.maxw-8, 'F1=Help')
            except:
                pass
        self.win_status.refresh()


    def show(self):
        """show title, files panel(s) and status bar"""
        
        self.__show_bars()
        for panel in self.panels:
            panel.show()
        

    def run(self):
        """run application"""

        while 1:
            self.show()
            oldpanel = self.panels[self.panel].manage_keys()
            if oldpanel < 0:
                if self.prefs.options['save_conf_at_exit']:
                    self.prefs.save()
                if oldpanel == -1:
                    for panel in self.panels:
                        if panel.vfs:
                            vfs.exit(app, panel)
                    return self.panels[self.panel].path
                else:
                    for panel in self.panels:
                        if panel.vfs:
                            vfs.exit(app, panel)
                    return
            # change panel active
            if oldpanel == 0:
                self.panel = 1
            else:
                self.panel = 0


    def get_otherpanel(self):
        """return the panel not active"""
        
        if self.panel == 0:
            return self.panels[1]
        else:
            return self.panels[0]


##################################################
##### panel
##################################################
class Panel:
    """Panel class"""
    
    def __init__(self, path, pos, app):
        self.maxh, self.maxw = app.maxh, app.maxw
        self.__calculate_columns()
        self.pos = pos
        self.init_curses(pos)
        self.init_dir(path, app)


    def __calculate_columns(self):
        self.pos_col2 = self.maxw / 2 - 14
        self.pos_col1 = self.pos_col2 - 8

        
    # GUI
    def __calculate_dims(self, pos=0):
        if pos == 0:      # not visible panel
            return (self.maxh-2, self.maxw, 0, 0)     # h, w, y, x
        elif pos == 1:    # left panel
            return (self.maxh-2, int(self.maxw/2), 1, 0)
        elif pos == 2:    # right panel
            return (self.maxh-2, int(self.maxw/2), 1, int(self.maxw/2))
        elif pos == 3:    # full panel
            return (self.maxh-2, self.maxw, 1, 0)     # h, w, y, x
        else:             # error
            messages.error('Initialize Panels',
                           'Incorrect panel number.\nLook for bugs if you can see this.')
            return (self.maxh-2, int(self.maxw/2), 1, int(self.maxw/2))


    def init_curses(self, pos=0):
        self.dims = self.__calculate_dims(pos)
        try:
            self.win_files = curses.newwin(self.dims[0], self.dims[1], self.dims[2], self.dims[3])
        except curses.error:
            print 'Can\'t create panel window'
            sys.exit(-1)
        self.win_files.keypad(1)
        if curses.has_colors():
            self.win_files.attrset(curses.color_pair(2))
            self.win_files.bkgdset(curses.color_pair(2))
        

    def do_resize(self, h, w):
        self.maxh, self.maxw = h, w
        self.dims = self.__calculate_dims(self.pos)
        self.win_files.resize(self.dims[0], self.dims[1])
        self.win_files.mvwin(self.dims[2], self.dims[3])
        self.__calculate_columns()
        self.fix_limits()

        
    def show(self):
        """show panel"""

        # invisible
        if self.pos == 0:
            return

        self.win_files.erase()
        if self.maxw < 65:
            return
        # headers
        if self.pos != 3:
            if self == app.panels[app.panel]:
                self.win_files.attrset(curses.color_pair(5))
                attr = curses.color_pair(6) | curses.A_BOLD
            else:
                self.win_files.attrset(curses.color_pair(2))
                attr = curses.color_pair(2)
            if not self.vfs:
                path = self.path
            else:
                path = vfs.join(app, self)
            if len(path) > int(self.maxw/2) - 5:
                title_path = '~' + path[-int(self.maxw/2)+5:]
            else:
                title_path = path
            self.win_files.box()
 
            self.win_files.addstr(0, 2, title_path, attr)
            self.win_files.addstr(1, 1, center('Name', self.pos_col1-2),
                                  curses.color_pair(2) | curses.A_BOLD)
            self.win_files.addstr(1, self.pos_col1 + 2, 'Size',
                                  curses.color_pair(2) | curses.A_BOLD)
            self.win_files.addstr(1, self.pos_col2 + 5, 'Date',
                                  curses.color_pair(2) | curses.A_BOLD)

        # files
        for i in range(self.file_z - self.file_a + 1):
            filename = self.sorted[i + self.file_a]
            try:
                self.selections.index(filename)
            except ValueError:
                attr = curses.color_pair(2)
            else:
                attr = curses.color_pair(10) | curses.A_BOLD
            # get file info
            res = files.get_fileinfo_dict(self.path, filename,
                                          self.files[filename])
            # full panel
            if self.pos == 3:
                buf = self.__get_fileinfo_str_long(res)
                self.win_files.addstr(i, 0, buf, attr)
            # left or right panels
            else:
                buf = self.__get_fileinfo_str_short(res)
                self.win_files.addstr(i + 2, 1, buf, attr)

        # vertical separators
        if self.pos != 3:
            self.win_files.vline(1, self.pos_col1,
                                 curses.ACS_VLINE, self.dims[0]-2)
            self.win_files.vline(1, self.pos_col2,
                                 curses.ACS_VLINE, self.dims[0]-2)

        # vertical scroll bar
        if self.pos != 0:
            if self.pos == 3:
                h = self.maxh - 2
            else:
                h = self.maxh - 5
            y0, n = calculate_scrollbar_dims(h, self.nfiles, self.file_i)
            if self.pos == 3:
                if n != 0:
                    self.win_files.vline(0, self.maxw - 1,
                                         curses.ACS_VLINE, h)
                self.win_files.vline(y0, self.maxw - 1, curses.ACS_CKBOARD, n)
                if self.file_a != 0:
                    self.win_files.vline(0, self.maxw - 1, '^', 1)
                    if n == 1 and (y0 == 0):
                        self.win_files.vline(1, self.maxw - 1,
                                             curses.ACS_CKBOARD, n)
                if self.nfiles - 1 > self.file_a + h - 1:
                    self.win_files.vline(h - 1, self.maxw - 1, 'v', 1)
                    if n == 1 and (y0 == h - 1):
                        self.win_files.vline(h - 2, self.maxw - 1,
                                             curses.ACS_CKBOARD, n)
            else:
                self.win_files.vline(y0 + 2, int(self.maxw/2) - 1,
                                     curses.ACS_CKBOARD, n)
                if self.file_a != 0:
                    self.win_files.vline(2, int(self.maxw/2) - 1, '^', 1)
                    if n == 1 and (y0 + 2 == 2):
                        self.win_files.vline(3, int(self.maxw/2) - 1,
                                             curses.ACS_CKBOARD, n)
                if self.nfiles - 1 > self.file_a + h - 1:
                    self.win_files.vline(h + 1, int(self.maxw/2) - 1, 'v', 1)
                    if n == 1 and (y0 + 2 == h + 1):
                        self.win_files.vline(h, int(self.maxw/2) - 1,
                                             curses.ACS_CKBOARD, n)

        self.win_files.refresh()
        self.__showbar()


    def __showbar(self):
        if self != app.panels[app.panel]:     # panel not active
            return
        if self.pos == 3:      # full panel
            cursorbar = curses.newpad(1, self.maxw)
        else:                  # left or right panel
            cursorbar = curses.newpad(1, int(self.maxw/2) - 1)

        cursorbar.attrset(curses.color_pair(3))
        cursorbar.bkgdset(curses.color_pair(3))
        filename = self.sorted[self.file_i]

        try:
            self.selections.index(filename)
        except ValueError:
            attr = curses.color_pair(3)
        else:
            attr = curses.color_pair(11) | curses.A_BOLD
        cursorbar.erase()
        # get file info
        res = files.get_fileinfo_dict(self.path, filename,
                                      self.files[filename])
        if self.pos == 3:
            buf = self.__get_fileinfo_str_long(res)
            cursorbar.addstr(0, 0, buf, attr)
            cursorbar.refresh(0, 0,
                              self.file_i % self.dims[0] + 1, 0,
                              self.file_i % self.dims[0] + 1, self.maxw - 2)
        else:
            buf = self.__get_fileinfo_str_short(res)
            cursorbar.addstr(0, 0, buf, attr)
            cursorbar.addch(0, self.pos_col1-1, curses.ACS_VLINE)
            cursorbar.addch(0, self.pos_col2-1, curses.ACS_VLINE)
            if self.pos == 1:
                cursorbar.refresh(0, 0,
                                  self.file_i % (self.dims[0]-3) + 3, 1,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  int(self.maxw/2) - 2)
            else:
                cursorbar.refresh(0, 0,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  int(self.maxw/2) + 1,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  self.maxw - 2)


    def __get_fileinfo_str_short(self, res):
        filewidth = self.maxw/2-24
        fname = res['filename']
        if len(fname) > filewidth:
            half = int(filewidth / 2)
            fname = fname[:half+2] + '~' + fname[-half+3:]
        fname = ljust(fname, self.pos_col1-2)
        if res['dev']:
            buf = '%c%s %3d,%3d %12s' % \
                  (res['type_chr'], fname,
                   res['maj_rdev'], res['min_rdev'],
                   res['mtime2'])
        else:
            buf = '%c%s %7s %12s' % \
                  (res['type_chr'], fname,
                   res['size'], res['mtime2'])                    
        return buf


    def __get_fileinfo_str_long(self, res):
        fname = res['filename']
        if len(fname) > self.maxw-57:
            half = int((self.maxw-57) / 2)
            fname = fname[:half+2] + '~' + fname[-half+2:]
        if res['dev']:
            buf = '%c%9s %-8s %-8s %3d,%3d  %16s  %s' % \
                  (res['type_chr'], res['perms'],
                   res['owner'], res['group'],
                   res['maj_rdev'], res['min_rdev'],
                   res['mtime'], fname)
        else:
            buf = '%c%9s %-8s %-8s %7s  %16s  %s' % \
                  (res['type_chr'], res['perms'],
                   res['owner'], res['group'],
                   res['size'],
                   res['mtime'], fname)
        return buf


    # Files
    def init_dir(self, path, application = None):
        try:
            # HACK: hack to achieve to pass prefs to this function
            #       the first time it is executed
            if application != None:
                self.nfiles, self.files = files.get_dir(path, application.prefs.options['show_dotfiles'])
                sortmode = application.modes['sort']
                sort_mix_dirs = application.modes['sort_mix_dirs']
                sort_mix_cases = application.modes['sort_mix_cases']
            else:
                self.nfiles, self.files = files.get_dir(path, app.prefs.options['show_dotfiles'])
                sortmode = app.modes['sort']
                sort_mix_dirs = app.modes['sort_mix_dirs']
                sort_mix_cases = app.modes['sort_mix_cases']
            self.sorted = files.sort_dir(self.files, sortmode,
                                         sort_mix_dirs, sort_mix_cases)
            self.file_i = self.file_a = self.file_z = 0
            self.fix_limits()
            self.path = os.path.abspath(path)
            self.selections = []
        except (IOError, OSError), (errno, strerror):
            messages.error('Enter In Directory', '%s (%d)' %
                           (strerror, errno), path)
            # if not initialized, python can retrive app.initialized variable,
            # so the try-except statement
            try:
                if not app.initialized:
                    sys.exit(-1)
            except:
                lfm_exit(-1)
                return
        # vfs variables
        self.vfs = ''          # vfs? if not -> blank string
        self.base = ''         # tempdir basename
        self.vbase = self.path # virtual directory basename
        


    def fix_limits(self):
        if self.file_i < 0:
            self.file_i = 0
        if self.file_i > self.nfiles - 1:
            self.file_i = self.nfiles - 1
        if self.pos == 3 or self.pos == 0:    # full or invisible panel
            height = self.dims[0]
        else:                                 # left or right panel
            height = self.dims[0] - 3
        self.file_a = int(self.file_i / height) * height
        self.file_z = self.file_a + height - 1
        if self.file_z > self.nfiles - 1:
            self.file_z = self.nfiles - 1


    def refresh_panel(self, panel):
        """this is needed because panel could be changed"""

        path = panel.path
        if path[-1] == os.sep:
            path = path[:-1]
        while not os.path.exists(path):
            path = os.path.dirname(path)

        if path != panel.path:
            panel.path = path
            panel.file_i = 0
            pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
            panel.init_dir(panel.path)
            panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
            panel.fix_limits()
            panel.selections = []
        else:
            filename_old = panel.sorted[panel.file_i]
            selections_old = panel.selections[:]
            pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
            panel.init_dir(panel.path)
            panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
            try:
                panel.file_i = panel.sorted.index(filename_old)
            except ValueError:
                panel.file_i = 0
            panel.fix_limits()
            panel.selections = selections_old[:]
            for f in panel.selections:
                if f not in panel.sorted:
                    panel.selections.remove(f)


    # Keys
    def manage_keys(self):
        while 1:
            app.show()
            ch = self.win_files.getch()
            if ch == 0x1B:     # ESC
                ch = self.win_files.getch() + 0x400
#             print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                   (curses.keyname(ch), ch & 255, ch, ch)
#             messages.win('Keyboard hitted:',
#                          'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                          (curses.keyname(ch), ch & 255, ch, ch))
            ret = actions.do(app, self, ch)
            if ret != None:
                return ret

#             # refresh screen
#             elif ch in [0x12]:             # Ctrl-r
#                 app.show()
#                 self.refresh_panel(self)
#                 self.refresh_panel(app.get_otherpanel())


##################################################
##### Wrappers
##################################################
def cursor_show():
    try:
        curses.curs_set(1)
    except:
        pass


def cursor_hide():
    try:
        curses.curs_set(0)
    except:
        pass


##################################################
##### Utils
##################################################
def center(s, maxlen):
    return s.center(maxlen)[:maxlen]
    

def ljust(s, maxlen):
    return s.ljust(maxlen)[:maxlen]
    

def rjust(s, maxlen):
    return s.rjust(maxlen)[maxlen:]
    

def num2str(num):
    num_list = []
    while num / 1000.0 >= 0.001:
        num_list.append('%.3d' % (num % 1000))
        num /= 1000.0
    else:
        num_str = '0'
    if len(num_list) != 0:
        num_list.reverse()
        num_str = ','.join(num_list)
        while num_str[0] == '0':
            num_str = num_str[1:]
    return num_str


def calculate_scrollbar_dims(h, nels, i):
    """calculate scrollbar initial position and size"""

    if nels > h:
        n = int(h * h / nels)
        if n == 0:
            n = 1
        a = int(i / h) * h
        y0 = int(a * h / nels)
        if y0 < 0:
            y0 = 0
        elif y0 + n > h:
            y0 = h - n
    else:
        y0 = 0
        n = 0
    return y0, n


##################################################
##### Main
##################################################
def usage(prog, msg = ""):
    prog = os.path.basename(prog)
    if msg != "":
        print '%s:\t%s\n' % (prog, msg)
    print """\
%s v%s - (C) %s, by %s

A program trying to recover command line good ol' times feelings...
Released under GNU Public License, read COPYING for more details.

Usage:\t%s\t[-h | --help]
\t\t[-d | --debug]
\t\t[-1 | -2] [pathtodir1 | pathtofile [pathtodir2]]
Options:
    -1\t\t\tstart in 1 panel mode
    -2\t\t\tstart in 2 panels mode (default)
    -d, --debug\t\tcreate debug file
    -h, --help\t\tshow help
    pathtodir1\t\tdirectory
    pathtofile\t\tfile to view/edit
    pathtodir2\t\tdirectory to show in panel 2\
""" % (LFM_NAME, VERSION, DATE, AUTHOR, prog)


def lfm_exit(ret_code, ret_path='.'):
    f = open('/tmp/lfm-%s.path' % (os.getppid()), 'w')
    f.write(ret_path)
    f.close()
    sys.exit(ret_code)


def main(win, path, npanels):
    global app

    app = Lfm(win, path, npanels)
    if app == OSError:
        sys.exit(-1)
    ret = app.run()
    return ret

    
def LfmApp(sysargs):
    import getopt

    # defaults
    DEBUG = 0
    npanels = 2
    paths = []
   
    # args
    try:
        opts, args = getopt.getopt(sysargs[1:], '12dh',
                                   ['', '', 'debug', 'help'])
    except getopt.GetoptError:
        usage(sysargs[0], 'Bad argument(s)')
        lfm_exit(-1)
    for o, a in opts:
        if o == '-1':
            npanels = 1
        if o == '-2':
            npanels = 2
        if o in ('-d', '--debug'):
            DEBUG = 1
        if o in ('-h', '--help'):
            usage(sysargs[0])
            lfm_exit(2)

    if len(args) == 0:
        paths.append(os.path.abspath('.'))
        paths.append(os.path.abspath('.'))
    elif len(args) == 1:
        buf = os.path.abspath(args[0])
        if not os.path.isdir(buf):
            if os.path.isfile(buf):
                # edit/view file
                pass
            else:
                usage(sysargs[0], '<%s> is not a file or directory' % args[0])
                lfm_exit(-1)
        paths.append(buf)
        paths.append(os.path.abspath('.'))
    elif len(args) == 2:
        buf = os.path.abspath(args[0])
        if not os.path.isdir(buf):
            usage(sysargs[0], '<%s> is not a file or directory' % args[0])
            lfm_exit(-1)
        paths.append(buf)
        buf = os.path.abspath(args[1])
        if not os.path.isdir(buf):
            usage(sysargs[0], '<%s> is not a file or directory' % args[1])
            lfm_exit(-1)
        paths.append(buf)
    else:
        usage(sysargs[0], 'Incorrect number of arguments')
        lfm_exit(-1)

    DEBUGFILE = './lfm-log.debug'
    if DEBUG:
        debug = open(DEBUGFILE, 'w')
        debug.write('********** Start:   ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        sys.stdout = debug
        sys.stderr = debug

    path = curses.wrapper(main, paths, npanels)

    if DEBUG:
        debug.write('********** End:     ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        debug.close()

    sys.stdout = sys.__stdout__
    sys.stdout = sys.__stderr__

    if path != None:
        lfm_exit(0, path)
    else:
        lfm_exit(0)


if __name__ == '__main__':
    LfmApp(sys.argv)
