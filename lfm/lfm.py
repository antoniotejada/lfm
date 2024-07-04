#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2001-8  Iñigo Serna
# Time-stamp: <2008-12-20 22:48:01 inigo>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


u"""lfm v2.1 - (C) 2001-8, by Iñigo Serna <inigoserna@gmail.com>

'Last File Manager' is a file manager for UNIX console which born with
midnight commander as model. Released under GNU Public License, read
COPYING file for more details.

Usage:\tlfm <options> [path1 [path2]]

Arguments:
    path1            Directory to show in left pane
    path2            Directory to show in right pane

Options:
    -1               Start in 1-pane mode
    -2               Start in 2-panes mode (default)
    -d, --debug      Create debug file
    -h, --help       Show help
"""


__author__ = u'Iñigo Serna'
__revision__ = '2.1'


import os, os.path
import sys
import time
import getopt
import logging
import curses

from __init__ import *
from config import Config, colors
import files
import actions
import utils
import vfs
import messages
import pyview


######################################################################
##### Global variables
LOG_FILE = os.path.join(os.getcwd(), 'lfm.log')
MAX_HISTORIC_ENTRIES = 15


######################################################################
##### Lfm main class
class Lfm(object):
    """Main application class"""

    def __init__(self, win, prefs):
        self.win = win              # root window, needed for resizing
        self.prefs = prefs          # preferences
        self.init_ui()
        self.statusbar = StatusBar(self.maxh, self)   # statusbar
        self.lpane = Pane(PANE_MODE_LEFT, self)  # left pane
        self.rpane = Pane(PANE_MODE_RIGHT, self) # right pane
        self.act_pane, self.noact_pane = self.lpane, self.rpane
        if self.prefs.options['num_panes'] == 1:
            self.lpane.mode = PANE_MODE_FULL
            self.lpane.init_ui()
            self.rpane.mode = PANE_MODE_HIDDEN
            self.rpane.init_ui()
        actions.app = messages.app = utils.app = vfs.app = pyview.app = self


    def load_paths(self, paths1, paths2):
        self.lpane.load_tabs_with_paths(paths1)
        self.rpane.load_tabs_with_paths(paths2)


    def init_ui(self):
        """initialize curses stuff: windows, colors..."""

        self.maxh, self.maxw = self.win.getmaxyx()
        curses.cbreak()
        curses.raw()
        self.win.leaveok(1)
        messages.cursor_hide()

        # colors
        if curses.has_colors():
            # Translation table: color name -> curses color name
            colors_table = {
                'black': curses.COLOR_BLACK,
                'blue': curses.COLOR_BLUE,
                'cyan': curses.COLOR_CYAN,
                'green': curses.COLOR_GREEN,
                'magenta': curses.COLOR_MAGENTA,
                'red': curses.COLOR_RED,
                'white': curses.COLOR_WHITE,
                'yellow': curses.COLOR_YELLOW }
            # List of items to get color
            color_items = ['title', 'files', 'current_file', 'messages', 'help',
                           'file_info', 'error_messages1', 'error_messages2',
                           'buttons', 'selected_file', 'current_selected_file',
                           'tabs', 'temp_files', 'document_files', 'media_files',
                           'archive_files', 'source_files', 'graphics_files',
                           'data_files', 'current_file_otherpane',
                           'current_selected_file_otherpane']
            # Initialize every color pair with user colors or with the defaults
            prefs_colors = self.prefs.colors
            for i, item_name in enumerate(color_items):
                pref_color_fg, pref_color_bg = prefs_colors[item_name]
                def_color_fg = colors_table[colors[item_name][0]]
                def_color_bg = colors_table[colors[item_name][1]]
                color_fg = colors_table.get(pref_color_fg, def_color_fg)
                color_bg = colors_table.get(pref_color_bg, def_color_bg)
                curses.init_pair(i+1, color_fg, color_bg)


    def resize(self):
        """resize windows"""

        h, w = self.win.getmaxyx()
        self.maxh, self.maxw = h, w
        if w == 0 or h == 2:
            return
        self.win.resize(h, w)
        self.lpane.do_resize(h, w)
        self.rpane.do_resize(h, w)
        self.statusbar.do_resize(h, w)
        self.regenerate()
        self.display()


    def display(self):
        """display/update both panes and status bar"""

        self.lpane.display()
        self.rpane.display()
        self.statusbar.display()


    def half_display(self):
        """display/update only active pane and status bar"""

        self.act_pane.display()
        self.statusbar.display()


    def half_display_other(self):
        """display/update only non-active pane and status bar"""

        self.noact_pane.display()
        self.statusbar.display()


    def regenerate(self):
        """Rebuild panes' directories"""

        self.lpane.regenerate()
        self.rpane.regenerate()


    def quit_program(self, icode):
        """save settings and prepare to quit"""

        for tab in self.lpane.tabs + self.rpane.tabs:
            if tab.vfs:
                vfs.exit(tab)
        if self.prefs.options['save_conf_at_exit']:
            self.prefs.save()
        if icode == -1: # change directory
            return self.act_pane.act_tab.path
        else:           # exit, but don't change directory
            return


    def run(self):
        """run application"""

        while True:
            self.display()
            ret = self.act_pane.manage_keys()
            if ret < 0:
                return self.quit_program(ret)
            elif ret == RET_TOGGLE_PANE:
                if self.act_pane == self.lpane:
                    self.act_pane, self.noact_pane = self.rpane, self.lpane
                else:
                    self.act_pane, self.noact_pane = self.lpane, self.rpane
            elif ret == RET_TAB_NEW:
                tab = self.act_pane.act_tab
#                 path = os.path.dirname(tab.vbase) if tab.vfs else tab.path
                if tab.vfs:
                    path = os.path.dirname(tab.vbase)
                else:
                    path = tab.path
                idx = self.act_pane.tabs.index(tab)
                newtab = TabVfs(self.act_pane)
                newtab.init(path)
                self.act_pane.tabs.insert(idx+1, newtab)
                self.act_pane.act_tab = newtab
            elif ret == RET_TAB_CLOSE:
                tab = self.act_pane.act_tab
                idx = self.act_pane.tabs.index(tab)
                self.act_pane.act_tab = self.act_pane.tabs[idx-1]
                self.act_pane.tabs.remove(tab)
                del tab


######################################################################
##### StatusBar class
class StatusBar(object):
    """Status bar"""

    def __init__(self, maxh, app):
        self.app = app
        try:
            self.win = curses.newwin(1, 0, maxh-1, 0)
        except curses.error:
            print 'Can\'t create StatusBar window'
            sys.exit(-1)
        if curses.has_colors():
            self.win.bkgd(curses.color_pair(1))


    def do_resize(self, h, w):
        self.win.resize(1, w)
        self.win.mvwin(h-1, 0)


    def display(self):
        """show status bar"""

        self.win.erase()
        adir = self.app.act_pane.act_tab
        maxw = self.app.maxw
        if len(adir.selections):
            if maxw >= 45:
                size = 0
                for f in adir.selections:
                    size += adir.files[f][files.FT_SIZE]
                self.win.addstr('    %s bytes in %d files' % \
                                (num2str(size), len(adir.selections)))
        else:
            if maxw >= 80:
                self.win.addstr('File: %4d of %-4d' % \
                                (adir.file_i + 1, adir.nfiles))
                filename = adir.sorted[adir.file_i]
                if adir.vfs:
                    realpath = os.path.join(vfs.join(self.app.act_pane.act_tab),
                                            filename)
                else:
                    realpath = files.get_realpath(adir.path, filename,
                                                  adir.files[filename][files.FT_TYPE])
                realpath = utils.decode(realpath)
                if len(realpath) > maxw - 35:
                    path = '~' + realpath[-(maxw-37):]
                else:
                    path = realpath
                path = utils.encode(path)
                self.win.addstr(0, 20, 'Path: ' + path)
        if maxw > 10:
            try:
                self.win.addstr(0, maxw-8, 'F1=Help')
            except:
                pass
        self.win.refresh()


######################################################################
##### Pane class
class Pane(object):
    """The Pane class is like a notebook containing TabVfs"""

    def __init__(self, mode, app):
        self.app = app
        self.mode = mode
        self.dims = [0, 0, 0, 0]    # h, w, y0, x0
        self.maxh, self.maxw = app.maxh, app.maxw
        self.init_ui()
        self.tabs = []


    def load_tabs_with_paths(self, paths):
        for path in paths:
            tab = TabVfs(self)
            err = tab.init(path)
            if err:
                tab.init(os.path.abspath('.'))
            self.tabs.append(tab)
        self.act_tab = self.tabs[0]


    def init_ui(self):
        self.dims = self.__calculate_dims()
        try:
            self.win = curses.newwin(*self.dims)
        except curses.error:
            print 'Can\'t create Pane window'
            sys.exit(-1)
        self.win.leaveok(1)
        self.win.keypad(1)
        if curses.has_colors():
            self.win.bkgd(curses.color_pair(2))
        self.__calculate_columns()


    def __calculate_dims(self):
        if self.mode == PANE_MODE_HIDDEN:
            return (self.maxh-2, self.maxw, 0, 0)     # h, w, y0, x0
        elif self.mode == PANE_MODE_LEFT:
            return (self.maxh-2, int(self.maxw/2), 1, 0)
        elif self.mode == PANE_MODE_RIGHT:
            return (self.maxh-2, self.maxw-int(self.maxw/2), 1, int(self.maxw/2))
        elif self.mode == PANE_MODE_FULL:
            return (self.maxh-2, self.maxw, 1, 0)     # h, w, y0, x0
        else:              # error
            messages.error('Initialize Panes Error',
                           'Incorrect pane number.\nLook for bugs if you can see this.')
            return (self.maxh-2, int(self.maxw/2), 1, int(self.maxw/2))


    def __calculate_columns(self):
        self.pos_col2 = self.dims[1] - 14 # sep between size and date
        self.pos_col1 = self.pos_col2 - 8 # sep between filename and size


    def do_resize(self, h, w):
        self.maxh, self.maxw = h, w
        self.dims = self.__calculate_dims()
        self.win.resize(self.dims[0], self.dims[1])
        self.win.mvwin(self.dims[2], self.dims[3])
        self.__calculate_columns()
        for tab in self.tabs:
            tab.fix_limits()


    def display(self):
        """display pane"""

        if self.mode == PANE_MODE_HIDDEN:
            return
        if self.maxw < 65:
            return
        self.display_tabs()
        self.display_files()
        self.display_cursorbar()


    def display_tabs(self):
        tabs = curses.newpad(1, self.dims[1]+1)
        tabs.bkgd(curses.color_pair(12))
        tabs.erase()
        w = self.dims[1] / 4
        if w < 10:
            w = 5
        tabs.addstr(('[' + ' '*(w-2) + ']') * len(self.tabs))
        for i, tab in enumerate(self.tabs):
            if w < 10:
                path = '[ %d ]' % (i+1, )
            else:
                if tab.vfs:
                    path = os.path.basename(tab.vbase.split('#')[0])
                else:
                    path = os.path.basename(tab.path) or os.path.dirname(tab.path)
                path = utils.decode(path)
                if len(path) > w - 2:
                    path = '[%s~]' % path[:w-3]
                else:
                    path = '[' + path + ' ' * (w-2-len(path)) + ']'
                path = utils.encode(path)
#             attr = curses.color_pair(10) if tab == self.act_tab else curses.color_pair(1)
            if tab == self.act_tab:
                attr = curses.color_pair(10) #| curses.A_BOLD
            else:
                attr = curses.color_pair(1)
            tabs.addstr(0, i*w, path, attr)
        tabs.refresh(0, 0, 0, self.dims[3],  1, self.dims[3]+self.dims[1]-1)


    def get_filetypecolorpair(self, f, typ):
        if typ == files.FTYPE_DIR:
            return curses.color_pair(5)
        elif typ == files.FTYPE_EXE:
            return curses.color_pair(6)  | curses.A_BOLD
        ext = os.path.splitext(f)[1].lower()
        files_ext = self.app.prefs.files_ext
        if ext in files_ext['temp_files']:
            return curses.color_pair(13)
        elif ext in files_ext['document_files']:
            return curses.color_pair(14)
        elif ext in files_ext['media_files']:
            return curses.color_pair(15)
        elif ext in files_ext['archive_files']:
            return curses.color_pair(16)
        elif ext in files_ext['source_files']:
            return curses.color_pair(17)
        elif ext in files_ext['graphics_files']:
            return curses.color_pair(18)
        elif ext in files_ext['data_files']:
            return curses.color_pair(19)
        else:
            return curses.color_pair(2)


    def display_files(self):
        tab = self.act_tab
        self.win.erase()

        # calculate pane width, height and vertical start position
        w = self.dims[1]
        if self.mode != PANE_MODE_FULL:
            h, y = self.maxh-5, 2
        else:
            h, y = self.maxh-2, 0

        # headers
        if self.mode != PANE_MODE_FULL:
            if self == self.app.act_pane:
                self.win.attrset(curses.color_pair(5))
                attr = curses.color_pair(6) | curses.A_BOLD
            else:
                self.win.attrset(curses.color_pair(2))
                attr = curses.color_pair(2)
#             path = utils.decode(vfs.join(tab) if tab.vfs else tab.path)
            if tab.vfs:
                path = vfs.join(tab)
            else:
                path = tab.path
            path = utils.decode(path)
#             title_path = utils.encode('~' + path[-w+5:] if len(path) > w-5 else path)
            if len(path) > w - 5:
                title_path = '~' + path[-w+5:]
            else:
                title_path = path
            title_path = utils.encode(title_path)
            self.win.box()
            self.win.addstr(0, 2, title_path, attr)
            self.win.addstr(1, 1,
                            'Name'.center(self.pos_col1-2)[:self.pos_col1-2],
                            curses.color_pair(2) | curses.A_BOLD)
            self.win.addstr(1, self.pos_col1+2, 'Size',
                            curses.color_pair(2) | curses.A_BOLD)
            self.win.addstr(1, self.pos_col2+5, 'Date',
                            curses.color_pair(2) | curses.A_BOLD)
        else:
            if tab.nfiles > h:
                self.win.vline(0, w-1, curses.ACS_VLINE, h)

        # files
        for i in xrange(tab.file_z - tab.file_a + 1):
            filename = tab.sorted[i+tab.file_a]
            # get file info
            res = files.get_fileinfo_dict(tab.path, filename,
                                          tab.files[filename])
            # get file color
            if tab.selections.count(filename):
                attr = curses.color_pair(10) | curses.A_BOLD
            else:
                if self.app.prefs.options['color_files']:
                    attr = self.get_filetypecolorpair(filename, tab.files[filename][files.FT_TYPE])
                else:
                    attr = curses.color_pair(2)

            # show
            if self.mode == PANE_MODE_FULL:
                buf = tab.get_fileinfo_str_long(res, w)
                self.win.addstr(i, 0, buf, attr)
            else:
                buf = tab.get_fileinfo_str_short(res, w, self.pos_col1)
                self.win.addstr(i+2, 1, buf, attr)

        # vertical separators
        if self.mode != PANE_MODE_FULL:
            self.win.vline(1, self.pos_col1, curses.ACS_VLINE, self.dims[0]-2)
            self.win.vline(1, self.pos_col2, curses.ACS_VLINE, self.dims[0]-2)

        # vertical scroll bar
        y0, n = self.__calculate_scrollbar_dims(h, tab.nfiles, tab.file_i)
        self.win.vline(y+y0, w-1, curses.ACS_CKBOARD, n)
        if tab.file_a != 0:
            self.win.vline(y, w-1, '^', 1)
            if (n == 1) and (y0 == 0):
                self.win.vline(y+1, w-1, curses.ACS_CKBOARD, n)
        if tab.nfiles  > tab.file_a + h:
            self.win.vline(h+y-1, w-1, 'v', 1)
            if (n == 1) and (y0 == h-1):
                self.win.vline(h+y-2, w-1, curses.ACS_CKBOARD, n)

        self.win.refresh()


    def __calculate_scrollbar_dims(self, h, nels, i):
        """calculate scrollbar initial position and size"""

        if nels > h:
            n = max(int(h*h/nels), 1)
            y0 = min(max(int(int(i/h)*h*h/nels),0), h-n)
        else:
            y0 = n = 0
        return y0, n


    def display_cursorbar(self):
        if self == self.app.act_pane:
            attr_noselected = curses.color_pair(3)
            attr_selected = curses.color_pair(11) | curses.A_BOLD
        else:
            if self.app.prefs.options['manage_otherpane']:
                attr_noselected = curses.color_pair(20)
                attr_selected = curses.color_pair(21)
            else:
                return
        if self.mode == PANE_MODE_FULL:
            cursorbar = curses.newpad(1, self.maxw)
        else:
            cursorbar = curses.newpad(1, self.dims[1]-1)
        cursorbar.bkgd(curses.color_pair(3))
        cursorbar.erase()

        tab = self.act_tab
        filename = tab.sorted[tab.file_i]

        try:
            tab.selections.index(filename)
        except ValueError:
            attr = attr_noselected
        else:
            attr = attr_selected

        res = files.get_fileinfo_dict(tab.path, filename, tab.files[filename])
        if self.mode == PANE_MODE_FULL:
            buf = tab.get_fileinfo_str_long(res, self.maxw)
            cursorbar.addstr(0, 0, buf, attr)
            cursorbar.refresh(0, 0,
                              tab.file_i % self.dims[0] + 1, 0,
                              tab.file_i % self.dims[0] + 1, self.maxw-2)
        else:
            buf = tab.get_fileinfo_str_short(res, self.dims[1], self.pos_col1)
            cursorbar.addstr(0, 0, buf, attr)
            cursorbar.addch(0, self.pos_col1-1, curses.ACS_VLINE, attr)
            cursorbar.addch(0, self.pos_col2-1, curses.ACS_VLINE, attr)
            row = tab.file_i % (self.dims[0]-3) + 3
            if self.mode == PANE_MODE_LEFT:
                cursorbar.refresh(0, 0,
                                  row, 1, row, int(self.maxw/2)-2)
            else:
                cursorbar.refresh(0, 0,
                                  row, int(self.maxw/2)+1, row, self.maxw-2)


    def regenerate(self):
        """Rebuild tabs' directories, this is needed because panel
        could be changed"""

        for tab in self.tabs:
            tab.backup()
            tab.regenerate()
            tab.fix_limits()
            tab.restore()


    def manage_keys(self):
        self.win.nodelay(1)
        while True:
            ch = self.win.getch()
            if ch == -1:       # no key pressed
#                 curses.napms(1)
                time.sleep(0.05)
                curses.doupdate()
                continue
#             print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                   (curses.keyname(ch), ch & 255, ch, ch)
#             messages.win('Keyboard hitted:',
#                          'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                          (curses.keyname(ch), ch & 255, ch, ch))
            ret = actions.do(self.act_tab, ch)
            if ret == None:
                self.app.display()
            elif ret == RET_NO_UPDATE:
                continue
            elif ret == RET_HALF_UPDATE:
                self.app.half_display()
            elif ret == RET_HALF_UPDATE_OTHER:
                self.app.half_display_other()
            else:
                return ret


######################################################################
##### Vfs class
class Vfs(object):
    """Vfs class contains files information in a directory"""

    def __init__(self):
        self.path = ''
        self.nfiles = 0
        self.files = []
        self.sorted = []
        self.selections = []
        self.sort_mode = 0
        # vfs variables
        self.vfs = ''          # vfs? if not -> blank string
        self.base = ''         # tempdir basename
        self.vbase = self.path # virtual directory basename
        # historic
        self.historic = []


    def init_dir(self, path):
#         old_path = self.path if self.path and not self.vfs else None
        if self.path and not self.vfs:
            old_path = self.path
        else:
            old_path = None
        try:
            app = self.pane.app
            self.nfiles, self.files = files.get_dir(path, app.prefs.options['show_dotfiles'])
            sortmode = app.prefs.options['sort']
            sort_mix_dirs = app.prefs.options['sort_mix_dirs']
            sort_mix_cases = app.prefs.options['sort_mix_cases']
            self.sorted = files.sort_dir(self.files, sortmode,
                                         sort_mix_dirs, sort_mix_cases)
            self.sort_mode = sortmode
            self.path = os.path.abspath(path)
            self.selections = []
        except (IOError, OSError), (errno, strerror):
            self.historic.pop()
            return (strerror, errno)
        # vfs variables
        self.vfs = ''
        self.base = ''
        self.vbase = self.path
        # historic
        if old_path:
            if old_path in self.historic:
                self.historic.remove(old_path)
            self.historic.append(old_path)
            self.historic = self.historic[-MAX_HISTORIC_ENTRIES:]


    def init(self, path, old_file = ''):
        raise NotImplementedError


    def enter_dir(self, filename):
        if self.vfs:
            if self.path == self.base and filename == os.pardir:
                vfs.exit(self)
                self.init(os.path.dirname(self.vbase),
                          old_file=os.path.basename(self.vbase).replace('#vfs', ''))
            else:
                pvfs, base, vbase = self.vfs, self.base, self.vbase
                self.init(os.path.join(self.path, filename))
                self.vfs, self.base, self.vbase = pvfs, base, vbase
        else:
            if filename == os.pardir:
                self.init(os.path.dirname(self.path),
                          old_file=os.path.basename(self.path))
            else:
                self.init(os.path.join(self.path, filename),
                          old_file=self.sorted[self.file_i],
                          check_oldfile=False)


    def exit_dir(self):
        if self.vfs:
            if self.path == self.base:
                vfs.exit(self)
                self.init(os.path.dirname(self.vbase),
                          old_file=os.path.basename(self.vbase).replace('#vfs', ''))
            else:
                pvfs, base, vbase = self.vfs, self.base, self.vbase
                self.init(os.path.dirname(self.path),
                          old_file=os.path.basename(self.path))
                self.vfs, self.base, self.vbase = pvfs, base, vbase
        else:
            if self.path != os.sep:
                self.init(os.path.dirname(self.path),
                          old_file=os.path.basename(self.path))


    def backup(self):
        self.old_file = self.sorted[self.file_i]
        self.old_file_i = self.file_i
        self.old_vfs = self.vfs, self.base, self.vbase


    def restore(self):
        try:
            self.file_i = self.sorted.index(self.old_file)
        except ValueError:
            if self.old_file_i < len(self.sorted):
                self.file_i = self.old_file_i
            else:
                self.file_i = len(self.sorted) - 1
        self.vfs, self.base, self.vbase = self.old_vfs
        del(self.old_file)
        del(self.old_file_i)
        del(self.old_vfs)


    def regenerate(self):
        """Rebuild tabs' directories"""

        path = self.path
        if path != "/" and path[-1] == os.sep:
            path = path[:-1]
        while not os.path.exists(path):
            path = os.path.dirname(path)

        if path != self.path:
            self.path = path
            self.file_i = 0
            pvfs, base, vbase = self.vfs, self.base, self.vbase
            self.init_dir(self.path)
            self.vfs, self.base, self.vbase = pvfs, base, vbase
            self.selections = []
        else:
            filename_old = self.sorted[self.file_i]
            selections_old = self.selections[:]
            pvfs, base, vbase = self.vfs, self.base, self.vbase
            self.init_dir(self.path)
            self.vfs, self.base, self.vbase = pvfs, base, vbase
            try:
                self.file_i = self.sorted.index(filename_old)
            except ValueError:
                self.file_i = 0
            self.selections = selections_old[:]
            for f in self.selections:
                if f not in self.sorted:
                    self.selections.remove(f)


    def refresh(self):
        file_i_old = self.file_i
        file_old = self.sorted[self.file_i]
        self.pane.app.regenerate()
        try:
            self.file_i = self.sorted.index(file_old)
        except ValueError:
            self.file_i = file_i_old
        self.fix_limits()


    def get_fileinfo_str_short(self, res, maxw, pos_col1):
        filewidth = maxw - 24
        fname = utils.decode(res['filename'])
        if len(fname) > filewidth:
            half = int(filewidth/2)
            fname = fname[:half+2] + '~' + fname[-half+3:]
        fname = fname.ljust(pos_col1-2)[:pos_col1-2]
        fname = utils.encode(fname)
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


    def get_fileinfo_str_long(self, res, maxw):
        filewidth = maxw - 57
        fname = utils.decode(res['filename'])
        if len(fname) > filewidth:
            half = int(filewidth/2)
            fname = fname[:half+2] + '~' + fname[-half+2:]
        fname = utils.encode(fname)
        if res['dev']:
            buf = '%c%9s %-8s %-8s %3d,%3d  %16s  %s' % \
                  (res['type_chr'], res['perms'],
                   res['owner'][:8], res['group'][:8],
                   res['maj_rdev'], res['min_rdev'],
                   res['mtime'], fname)
        else:
            buf = '%c%9s %-8s %-8s %7s  %16s  %s' % \
                  (res['type_chr'], res['perms'],
                   res['owner'][:8], res['group'][:8],
                   res['size'],
                   res['mtime'], fname)
        return buf


    def get_file(self):
        """return pointed file"""
        return self.sorted[self.file_i]


    def get_fullpathfile(self):
        """return full path for pointed file"""
        return os.path.join(self.path, self.sorted[self.file_i])


######################################################################
##### TabVfs class
class TabVfs(Vfs):
    """TabVfs class is the UI container for Vfs class"""

    def __init__(self, pane):
        Vfs.__init__(self)
        self.pane = pane


    def init(self, path, old_file = '', check_oldfile=True):
        err = self.init_dir(path)
        if err:
            messages.error('Enter In Directory', '%s (%d)' % err, path)
        if (check_oldfile and old_file) or (old_file and err):
            try:
                self.file_i = self.sorted.index(old_file)
            except ValueError:
                self.file_i = 0
        else:
            self.file_i = 0
        self.fix_limits()
        return err


    def fix_limits(self):
        self.file_i = max(0, min(self.file_i, self.nfiles-1))
        if self.pane.mode == PANE_MODE_HIDDEN or \
                self.pane.mode == PANE_MODE_FULL:
            height = self.pane.dims[0]
        else:
            height = self.pane.dims[0] - 3
        self.file_a = int(self.file_i/height) * height
        self.file_z = min(self.file_a+height-1, self.nfiles-1)


######################################################################
##### Utils
def num2str(num):
    # Fatal in #pys60
    # return (len(num) < 4) and num or (num2str(num[:-3]) + "." + num[-3:])
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


######################################################################
##### Main
def usage(msg = ''):
    if msg != "":
        print 'lfm:\tERROR: %s\n' % msg
    print __doc__


def lfm_exit(ret_code, ret_path='.'):
    f = open('/tmp/lfm-%s.path' % (os.getppid()), 'w')
    f.write(ret_path)
    f.close()
    sys.exit(ret_code)


def main(win, prefs, paths1, paths2):
    app = Lfm(win, prefs)
    app.load_paths(paths1, paths2)
    if app == OSError:
        sys.exit(-1)
    ret = app.run()
    return ret


def add_path(arg, paths):
    buf = os.path.abspath(arg)
    if not os.path.isdir(buf):
        usage('<%s> is not a directory' % arg)
        lfm_exit(-1)
    paths.append(buf)


def lfm_start(sysargs):
    # get configuration & preferences
    DEBUG = 0
    paths1, paths2 = [], []
    prefs = Config()
    ret = prefs.load()
    if ret == -1:
        print 'Config file does not exist, we\'ll use default values'
        prefs.save()
        time.sleep(1)
    elif ret == -2:
        print 'Config file looks corrupted, we\'ll use default values'
        prefs.save()
        time.sleep(1)

    # parse args
    # hack, 'lfm' shell function returns a string, not a list,
    # so we have to build a list
    if len(sysargs) <= 2:
        lst = sysargs[:]
        sysargs = [lst[0]]
        if len(lst) > 1:
            sysargs.extend(lst[1].split())
    try:
        opts, args = getopt.getopt(sysargs[1:], '12dh', ['debug', 'help'])
    except getopt.GetoptError:
        usage('Bad argument(s)')
        lfm_exit(-1)
    for o, a in opts:
        if o == '-1':
            prefs.options['num_panes'] = 1
        if o == '-2':
            prefs.options['num_panes'] = 2
        if o in ('-d', '--debug'):
            DEBUG = 1
        if o in ('-h', '--help'):
            usage()
            lfm_exit(2)

    if len(args) == 0:
        paths1.append(os.path.abspath('.'))
        paths2.append(os.path.abspath('.'))
    elif len(args) == 1:
        add_path(args[0], paths1)
        paths2.append(os.path.abspath('.'))
    elif len(args) == 2:
        add_path(args[0], paths1)
        add_path(args[1], paths2)
    else:
        usage('Incorrect number of arguments')
        lfm_exit(-1)

    # logging
    if DEBUG:
        log_file = os.path.join(os.path.abspath('.'), LOG_FILE)
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s\t%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S   ',
                            filename=log_file,
                            filemode='w')
    logging.info('Starting Lfm...')

    # main app
    logging.info('Main application call')
    path = curses.wrapper(main, prefs, paths1, paths2)
    logging.info('End')

    # change to directory
    if path != None:
        lfm_exit(0, path)
    else:
        lfm_exit(0)


if __name__ == '__main__':
    lfm_start(sys.argv)


######################################################################
