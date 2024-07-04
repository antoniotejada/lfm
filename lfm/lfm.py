#!/usr/bin/env python

# Copyright (C) 2001  Iñigo Serna
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
Copyright (C) 2001, Iñigo Serna <inigoserna@terra.es>.
All rights reserved.

This software has been realised under the GPL License, see the COPYING
file that comes with this package. There is NO WARRANTY.

'Last File Manager' is (tries to be) a simple 'midnight commander'-type
application for UNIX console.
"""


import os, os.path
import sys, time
import curses
from glob import glob

from lfm import files
from lfm import messages
from lfm import preferences
from lfm import pyview
#import files
#import messages
#import preferences
#import pyview


PROGNAME = 'lfm - Last File Manager'
VERSION = '0.7'
DATE = '2001'
AUTHOR = 'Iñigo Serna'

PREFSFILE = '.lfmrc'
DEBUG = 0


##################################################
##################################################
app = None
thread_quit = 0

defaultprogs = { 'shell': ('bash', 'ksh', 'tcsh', 'csh', 'sh'),
                 'pager': ('pyview', 'less', 'more', 'biew'),
                 'editor': ('mcedit', 'emacs', 'vi', 'joe'),
                 'find': ('find', ),
                 'egrep': ('egrep', 'grep'),
                 'tar': ('tar', ),
                 'gzip': ('gzip', ),
                 'bzip2': ('bzip2', ),
                 'web': ('galeon', 'mozilla', 'netscape', 'lynx', 'opera'),
                 'ogg': ('ogg123', ),
                 'mp3': ('mpg123', ),
                 'audio': ('esdplay', 'play', ),
                 'video': ('mplayer', 'xanim', 'aviplay'),
                 'graphics': ('ee', 'eog', 'gthumb', 'xv', 'gimp'),
                 'pdf' :('acroread', 'ggv', 'xpdf'),
                 'ps': ('ggv', 'gv'),
                 'tururu': ('tururu', 'sdfdsf', 'just to test') }

filetypes = { 'web': ('html', 'htm'),
              'ogg': ('ogg', ),
              'mp3': ('mp3', ),
              'audio': ('wav', 'au', 'midi'),
              'video': ('mpeg', 'mpg', 'avi', 'asf'),
              'graphics': ('png', 'jpeg', 'jpg', 'gif', 'tiff', 'tif', 'xpm'),
              'pdf': ('pdf', ),
              'ps': ('ps', ) }


##################################################
##### lfm
##################################################
class Lfm:
    """Main application class"""

    panels = []
    npanels = 0
    
    def __init__(self, paths, npanels = 2):
        self.npanels = npanels      # no. of panels showed
        self.panels = []            # list of panels
        self.panel = 0              # active panel
        # preferences
        self.prefs = preferences.Preferences(PREFSFILE, defaultprogs)
        self.modes = self.prefs.modes
        # panels
        self.init_curses()
        if npanels == 2:
            self.panels.append(Panel(paths[0], 1, self))     # left panel
            self.panels.append(Panel(paths[1], 2, self))     # right panel
        else:
            self.panels.append(Panel(paths[0], 3, self))     # full panel
            self.panels.append(Panel(paths[1], 0, self))     # not shown


    def init_curses(self):
        """initialize curses stuff: windows, colors, ..."""

        curses.cbreak()
        curses.raw()
        curses.curs_set(0)
        try:
            self.win_title = curses.newwin(1, 0, 0, 0)
            self.win_status = curses.newwin(1, 0, curses.LINES-1, 0)
        except curses.error:
            print 'Can\'t create windows'
            sys.exit(-1)

        # colors
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLUE)    # title
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)    # files
            curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_CYAN)      # current file
            curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_CYAN)   # messages
            curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)    # help
            curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)      # file info
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)      # error messages
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)      # error messages
            curses.init_pair(9, curses.COLOR_YELLOW, curses.COLOR_RED)     # button in dialog
            curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # file selected
            curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_CYAN)   # file selected and current
            self.win_title.attrset(curses.color_pair(1) | curses.A_BOLD)
            self.win_title.bkgdset(curses.color_pair(1))
            self.win_status.attrset(curses.color_pair(1))
            self.win_status.bkgdset(curses.color_pair(1))


    def show_bars(self):
        """show title and status bars"""
        
        self.win_title.erase()
        self.win_status.erase()

        title = '%s v%s   (c) %s, %s' % (PROGNAME, VERSION, DATE, AUTHOR)
        self.win_title.addstr(0, (curses.COLS-len(title))/2, title)

        panel = self.panels[self.panel]
        if len(panel.selections):
            size = 0
            for f in panel.selections:
                size += panel.files[f][files.FT_SIZE]
            size_list = []
            while size / 1000.0 > 0:
                size_list.append('%.3d' % (size % 1000))
                size /= 1000
            else:
                size_str = '0'
            if len(size_list) != 0:
                size_list.reverse()
                size_str = ','.join(size_list)
                while size_str[0] == '0':
                    size_str = size_str[1:]               
            self.win_status.addstr('    %s bytes in %d files' % \
                                   (size_str, len(panel.selections)))
        else:
            self.win_status.addstr('File: %4d of %-4d' % \
                                   (panel.file_i + 1, panel.nfiles))
            filename = panel.sorted[panel.file_i]
            realpath = files.get_realpath(panel.path, filename,
                                          panel.files[filename][files.FT_TYPE])
            if len(realpath) > curses.COLS - 35:
                path = '~' + realpath[-(curses.COLS-37):]
            else:
                path = realpath
            self.win_status.addstr(0, 20, 'Path: ' + path)
        self.win_status.addstr(0, curses.COLS-8, 'F1=Help')
        self.win_title.refresh()
        self.win_status.refresh()


    def show(self):
        """show title, files panel(s) and status bar"""
        
        self.show_bars()
        for panel in self.panels:
            panel.show()
        

    def run(self):
        """run application"""

        ret = self.prefs.load()
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
        while 1:
            self.show()
            oldpanel = self.panels[self.panel].manage_keys()
            if oldpanel < 0:
                if self.prefs.options['save_conf_at_exit']:
                    self.prefs.save()
                if oldpanel == -1:
                    return self.panels[self.panel].path
                else:
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
        self.pos = pos
        self.__init_curses()
        self.init_dir(path, app)


    # GUI
    def __init_curses(self):
        if self.pos == 0:      # not visible panel
            self.dims = (curses.LINES-2, 0, 0, 0)     # h, w, y, x
            return
        elif self.pos == 3:    # full panel
            self.dims = (curses.LINES-2, 0, 1, 0)     # h, w, y, x
        elif self.pos == 1:    # left panel
            self.dims = (curses.LINES-2, curses.COLS/2, 1, 0)
        else:                  # right panel
            self.dims = (curses.LINES-2, curses.COLS/2, 1, curses.COLS/2)
        try:
            self.win_files = curses.newwin(self.dims)
        except curses.error:
            print 'Can\'t create panel window'
            sys.exit(-1)
        self.win_files.keypad(1)
        if curses.has_colors():
            self.win_files.attrset(curses.color_pair(2))
            self.win_files.bkgdset(curses.color_pair(2))
        

    def show(self):
        """show panel"""

        # invisible
        if self.pos == 0:
            return

        self.win_files.erase()
        if self.pos != 3:
            if self == app.panels[app.panel]:
                self.win_files.attrset(curses.color_pair(5))
                attr = curses.color_pair(6) | curses.A_BOLD
            else:
                self.win_files.attrset(curses.color_pair(2))
                attr = curses.color_pair(2)
            if len(self.path) > curses.COLS/2 - 5:
                title_path = '~' + self.path[-35:]
            else:
                title_path = self.path
            self.win_files.box()
            self.win_files.addstr(0, 2, title_path, attr)
            self.win_files.addstr(1, 7, 'Name',
                                  curses.color_pair(2) | curses.A_BOLD)
            self.win_files.addstr(1, 20, 'Size',
                                  curses.color_pair(2) | curses.A_BOLD)
            self.win_files.addstr(1, 31, 'Date',
                                  curses.color_pair(2) | curses.A_BOLD)

        for i in range(self.file_z - self.file_a + 1):
            filename = self.sorted[i + self.file_a]
            try:
                self.selections.index(filename)
            except ValueError:
                attr = curses.color_pair(2)
            else:
                attr = curses.color_pair(10) | curses.A_BOLD
            # full panel
            if self.pos == 3:
                self.win_files.addstr(i, 0,
                                      files.get_fileinfostr(self.path, filename,
                                                            self.files[filename]),
                                      attr)
            # left or right panels
            else:
                self.win_files.addstr(i + 2, 1,
                                      files.get_fileinfostr_short(self.path,
                                                                  filename,
                                                                  self.files[filename]),
                                      attr)

        if self.pos != 3:
            self.win_files.vline(1, 18, curses.ACS_VLINE, self.dims[0]-2)
            self.win_files.vline(1, 26, curses.ACS_VLINE, self.dims[0]-2)

        if self.pos != 0:
            if self.pos == 3:
                h = curses.LINES - 2
            else:
                h = curses.LINES - 5
            if self.nfiles > h:
                n = h * h / self.nfiles
                if n == 0:
                    n = 1
                a = self.file_i /h * h
                y0 = a * h / self.nfiles
                if y0 < 0:
                    y0 = 0
                elif y0 + n > h:
                    y0 = h - n
            else:
                y0 = 0
                n = 0
            if self.pos == 3:
                if n != 0:
                    self.win_files.vline(0, curses.COLS - 1,
                                         curses.ACS_VLINE, h)
                self.win_files.vline(y0, curses.COLS - 1, curses.ACS_CKBOARD, n)
                if self.file_a != 0:
                    self.win_files.vline(0, curses.COLS - 1, '^', 1)
                    if n == 1 and (y0 == 0):
                        self.win_files.vline(1, curses.COLS - 1,
                                             curses.ACS_CKBOARD, n)
                if self.nfiles - 1 > self.file_a + h - 1:
                    self.win_files.vline(h - 1, curses.COLS - 1, 'v', 1)
                    if n == 1 and (y0 == h - 1):
                        self.win_files.vline(h - 2, curses.COLS - 1,
                                             curses.ACS_CKBOARD, n)
            else:
                self.win_files.vline(y0 + 2, curses.COLS/2 - 1,
                                     curses.ACS_CKBOARD, n)
                if self.file_a != 0:
                    self.win_files.vline(2, curses.COLS/2 - 1, '^', 1)
                    if n == 1 and (y0 + 2 == 2):
                        self.win_files.vline(3, curses.COLS/2 - 1,
                                             curses.ACS_CKBOARD, n)
                if self.nfiles - 1 > self.file_a + h - 1:
                    self.win_files.vline(h + 1, curses.COLS/2 - 1, 'v', 1)
                    if n == 1 and (y0 + 2 == h + 1):
                        self.win_files.vline(h, curses.COLS/2 - 1,
                                             curses.ACS_CKBOARD, n)

        self.win_files.refresh()
        self.__showbar()


    def __showbar(self):
        if self != app.panels[app.panel]:     # panel not active
            return
        if self.pos == 3:      # full panel
            cursorbar = curses.newpad(1, curses.COLS)
        else:                  # left or right panel
            cursorbar = curses.newpad(1, curses.COLS/2 - 1)

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
        if self.pos == 3:
            cursorbar.addstr(0, 0,
                             files.get_fileinfostr(self.path, filename,
                                                   self.files[filename]),
                             attr)
            cursorbar.refresh(0, 0,
                              self.file_i % self.dims[0] + 1, 0,
                              self.file_i % self.dims[0] + 1, curses.COLS - 2)
        else:
            cursorbar.addstr(0, 0,
                             files.get_fileinfostr_short(self.path, filename,
                                                         self.files[filename]),
                             attr)
            cursorbar.addch(0, 17, curses.ACS_VLINE)
            cursorbar.addch(0, 25, curses.ACS_VLINE)
            if self.pos == 1:
                cursorbar.refresh(0, 0,
                                  self.file_i % (self.dims[0]-3) + 3, 1,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  curses.COLS/2 - 2)
            else:
                cursorbar.refresh(0, 0,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  curses.COLS/2 + 1,
                                  self.file_i % (self.dims[0]-3) + 3,
                                  curses.COLS - 2)


    # Files
    def init_dir(self, path, application = None):
        try:
            self.nfiles, self.files = files.get_dir(path)
            # HACK: hack to achieve to pass prefs to this function
            #       the first time it is executed
            if application != None:
                sortmode = application.modes['sort']
                sort_mix_dirs = application.modes['sort_mix_dirs']
                sort_mix_cases = application.modes['sort_mix_cases']
            else:
                sortmode = app.modes['sort']
                sort_mix_dirs = app.modes['sort_mix_dirs']
                sort_mix_cases = app.modes['sort_mix_cases']
            self.sorted = files.sort_dir(self.files, sortmode,
                                         sort_mix_dirs, sort_mix_cases)
            self.file_i = self.file_a = self.file_z = 0
            self.fix_limits()
            self.path = os.path.abspath(path)
            self.selections = []
        except OSError, (errno, strerror):
            messages.error('Enter In Directory', '%s (%d)' %
                           (strerror, errno), path)
            app.show()
            return OSError


    def fix_limits(self):
        if self.file_i < 0:
            self.file_i = 0
        if self.file_i > self.nfiles - 1:
            self.file_i = self.nfiles - 1
        if self.pos == 3 or self.pos == 0:    # full or invisible panel
            height = self.dims[0]
        else:                                 # left or right panel
            height = self.dims[0] - 3
        self.file_a = self.file_i / height * height
        self.file_z = self.file_a + height - 1
        if self.file_z > self.nfiles - 1:
            self.file_z = self.nfiles - 1


    def refresh_panel(self, panel):
        """this is needed due to panel could be changed"""

        filename_old = panel.sorted[panel.file_i]
        selections_old = panel.selections[:]
        panel.init_dir(panel.path)
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
            chext = 0
            ch = self.win_files.getch()
#              print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                    (curses.keyname(ch), ch & 255, ch, ch)
#              messages.win('Keyboard hitted:',
#                           'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                           (curses.keyname(ch), ch & 255, ch, ch))


            # to avoid extra chars input
            if ch == 0x1B:
                chext = 1
                ch = self.win_files.getch()
                ch = self.win_files.getch()

            # cursor up
            if ch in [ord('p'), ord('P'), curses.KEY_UP]:
                self.file_i -= 1
                self.fix_limits()
            # cursor down
            elif ch in [ord('n'), ord('N'), curses.KEY_DOWN]:
                self.file_i += 1
                self.fix_limits()
            # page previous
            elif ch in [curses.KEY_PPAGE, curses.KEY_BACKSPACE,
                        0x08, 0x10]:                         # BackSpace, Ctrl-P
                self.file_i -= self.dims[0]
                if self.pos == 1 or self.pos == 2:
                    self.file_i += 3
                self.fix_limits()
            # page next
            elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:   # Ctrl-N
                self.file_i += self.dims[0]
                if self.pos == 1 or self.pos == 2:
                    self.file_i -= 3
                self.fix_limits()
            # home
            elif (ch in [curses.KEY_HOME, 348]) or \
                 (chext == 1) and (ch == 72):  # home
                self.file_i = 0
                self.fix_limits()
            # end
            elif (ch in [curses.KEY_END, 351]) or \
                 (chext == 1) and (ch == 70):   # end
                self.file_i = self.nfiles - 1
                self.fix_limits()
            
            # cursor left
            elif ch in [curses.KEY_LEFT]:
                if self.path != os.sep:
                    olddir = os.path.basename(self.path)
                    self.init_dir(os.path.dirname(self.path))
                    self.file_i = self.sorted.index(olddir)
                    self.fix_limits()
            # cursor right
            elif ch in [curses.KEY_RIGHT]:
                filename = self.sorted[self.file_i]
                if self.files[filename][files.FT_TYPE] == files.FTYPE_DIR:
                    self.init_dir(os.path.join(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
                    self.init_dir(files.get_linkpath(self.path, filename))
                else:
                    continue
            # go to directory
            elif ch in [ord('g'), ord('G')]:
                todir = doEntry('Go to directory', 'Type directory name')
                app.show()
                if todir == None or todir == "":
                    continue
                todir = os.path.join(self.path, todir)
                self.init_dir(todir)
                self.fix_limits()
            # go to file
            elif ch in [0x13]:             # Ctrl-S
                tofile = doEntry('Go to file', 'Type how file name begins')
                app.show()
                if tofile == None or tofile == "":
                    continue
                thefiles = self.sorted[self.file_i:]
                for f in thefiles:
                    if f.find(tofile) == 0:
                        break
                else:
                    continue
                self.file_i = self.sorted.index(f)
                self.fix_limits()

            # go to bookmark
            elif 0x30 <= ch <= 0x39:       # 0..9
                todir = app.prefs.bookmarks[ch - 0x30];
                self.init_dir(todir)
                self.fix_limits()
            # set bookmark
            elif ch in [ord('b'), ord('B')]:
                while 1:
                    ch = messages.get_a_key('Set bookmark',
                                            'Press 0-9 to save the bookmark in, Ctrl-C to quit')
                    if 0x30 <= ch <= 0x39:         # 0..9
                        app.prefs.bookmarks[ch-0x30] = self.path[:]
                        break
                    elif ch == -1:                 # Ctrl-C
                        break

            # show directories size
            elif ch in [ord('#')]:
                show_dirs_size(self)
            # sorting mode
            elif ch in [ord('s'), ord('S')]:
                app.show()
                sort(self)

            # tab => other panel
            elif ch in [ord('\t')]:
                if self.pos == 3:
                    continue
                return app.panel
            # toggle full panel / 2 panels
            elif ch in [ord('.')]:
                if self.pos == 3:
                    # now => 2 panels mode
                    app.panels[0].pos = 1
                    app.panels[1].pos = 2
                else:
                    # now => full panel mode
                    if app.panel == 0:
                        app.panels[0].pos = 3
                        app.panels[1].pos = 0
                    else:
                        app.panels[0].pos = 0
                        app.panels[1].pos = 3
                app.panels[0].__init_curses()
                app.panels[1].__init_curses()
                self.fix_limits()
            # change panels position
            elif ch in [ord(','), 0x15]:    # Ctrl-U
                if self.pos == 3:
                    continue                
                otherpanel = app.get_otherpanel()
                self.pos, otherpanel.pos = otherpanel.pos, self.pos
                self.__init_curses()
                otherpanel.__init_curses()
            # show the same directory in two panels
            elif ch in [ord('=')]:
                otherpanel = app.get_otherpanel()
                otherpanel.init_dir(self.path)
                otherpanel.fix_limits()
                
            # select item
            elif ch in [curses.KEY_IC]:
                filename = self.sorted[self.file_i]
                if filename == os.pardir:
                    self.file_i += 1
                    self.fix_limits()
                    continue
                try:
                    self.selections.index(filename)
                except ValueError:
                    self.selections.append(filename)
                else:
                    self.selections.remove(filename)
                self.file_i += 1
                self.fix_limits()
            # select group
            elif ch in [ord('+')]:
                pattern = doEntry('Select group', 'Type pattern', '*')
                if pattern == None or pattern == '':
                    continue
                fullpath = os.path.join(self.path, pattern)
                [self.selections.append(os.path.basename(f)) for f in glob(fullpath)]
            # deselect group
            elif ch in [ord('-')]:
                pattern = doEntry('Deselect group', 'Type pattern', '*')
                if pattern == None or pattern == '':
                    continue
                fullpath = os.path.join(self.path, pattern)
                for f in [os.path.basename(f) for f in glob(fullpath)]:
                    if f in self.selections:
                        self.selections.remove(f)
            # invert selections
            elif ch in [ord('*')]:
                selections_old = self.selections[:]
                self.selections = []
                for f in self.sorted:
                    if f not in selections_old and f != os.pardir:
                        self.selections.append(f)

            # enter
            elif ch in [10, 13]:
                filename = self.sorted[self.file_i]
                if self.files[filename][files.FT_TYPE] == files.FTYPE_DIR:
                    if filename == os.pardir:
                        olddir = os.path.basename(self.path)
                        self.init_dir(os.path.dirname(self.path))
                        self.file_i = self.sorted.index(olddir)
                        self.fix_limits()
                    else:
                        self.init_dir(os.path.join(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
                    self.init_dir(files.get_linkpath(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_EXE:
                    do_execute_file(self)
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_REG:
                    do_special_view_file(self)
                else:
                    continue

            # show file info
            elif ch in [ord('i') or ord('I')]:
                do_show_file_info(self)
            # do something on file
            elif ch in [ord('@')]:
                do_something_on_file(self)
            # special regards
            elif ch in [0xF1]:
                messages.win('Special Regards',
                             '  Maite zaitut, Montse\n   T\'estimo molt, Montse')
            # find/grep
            elif ch in [ord('/')]:
                findgrep(self)
            # touch file
            elif ch in [ord('t'), ord('T')]:
                newfile = doEntry('Touch file', 'Type file name')
                if newfile == None or newfile == "":
                    continue                      
                fullfilename = os.path.join(self.path, newfile)
                i, err = os.popen4('touch \"%s\"' % fullfilename)
                err = err.read().split(':')[-1:][0].strip()
                if err:
                    app.show()
                    messages.error('Touch file', '%s: %s' % (newfile, err))
                curses.curs_set(0)
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())
            # create link
            elif ch in [ord('l'), ord('L')]:
                pass
                otherpanel = app.get_otherpanel()
                if self.path != otherpanel.path:
                    otherfile = os.path.join(otherpanel.path,
                                             otherpanel.sorted[otherpanel.file_i])
                else:
                    otherfile = otherpanel.sorted[otherpanel.file_i]
                newlink, pointto = doDoubleEntry('Create link',
                                                 'Link name', '', 1, 1,
                                                 'Pointing to', otherfile, 1, 1)
                if newlink == None or pointto == None:
                    continue
                if newlink == '':
                    app.show()
                    messages.error('Edit link', 'You must type new link name')
                    continue                    
                if pointto == '':
                    app.show()
                    messages.error('Edit link', 'You must type pointed file')
                    continue
                fullfilename = os.path.join(self.path, newlink)
                ans = files.create_link(pointto, fullfilename)
                if ans:
                    app.show()
                    messages.error('Edit link', '%s (%s)' % (ans,
                                   self.sorted[self.file_i]))
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())
            # edit link
            elif ch in [0x0C]:             # Ctrl-L
                fullfilename = os.path.join(self.path, self.sorted[self.file_i])
                if not os.path.islink(fullfilename):
                    continue
                pointto = doEntry('Edit link', 'Link \'%s\' points to' % \
                                  self.sorted[self.file_i],
                                  os.readlink(fullfilename))
                if pointto == None or pointto == "":
                    continue
                if pointto != None and pointto != "" and \
                   pointto != os.readlink(fullfilename):
                    ans = files.modify_link(pointto, fullfilename)
                    if ans:
                        app.show()
                        messages.error('Edit link', '%s (%s)' % (ans,
                                       self.sorted[self.file_i]))
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())

            # shell
            elif ch in [0x0F]:             # Ctrl-O
                curses.endwin()
                os.system('cd \"%s\"; %s' % (self.path,
                                             app.prefs.progs['shell']))
                curses.curs_set(0)
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())
            # view
            elif ch in [ord('v'), ord('V'), curses.KEY_F3]:
                do_view_file(self)
            # edit
            elif ch in [ord('e'), ord('E'), curses.KEY_F4]:
                do_edit_file(self)
            # copy
            elif ch in [ord('c'), ord('C'), curses.KEY_F5]:
                otherpanel = app.get_otherpanel()
                destdir = otherpanel.path + os.sep
                if len(self.selections):
                    buf = 'Copy %d items to' % len(self.selections)
                    destdir = doEntry('Copy', buf, destdir)
                    if destdir:
                        overwrite_all = 0
                        for f in self.selections:
                            if not overwrite_all:
                                if app.prefs.confirmations['overwrite']:
                                    ans = run_thread('Copying \'%s\'' % f,
                                                     files.copy,
                                                     self.path, f, destdir)
                                    if type(ans) == type(''):
                                        app.show()
                                        ans2 = messages.confirm_all('Copy', 'Overwrite \'%s\'' % ans, 1)
                                        if ans2 == -1:
                                            break
                                        elif ans2 == 2:
                                            overwrite_all = 1
                                        if ans2 != 0:
                                            ans = run_thread('Copying \'%s\'' % f,
                                                             files.copy,
                                                             self.path, f,
                                                             destdir, 0)
                                        else:
                                            continue
                                else:
                                    ans = run_thread('Copying \'%s\'' % f,
                                                     files.copy,
                                                     self.path, f, destdir, 0)
                            else:
                                ans = run_thread('Copying \'%s\'' % f, files.copy,
                                                 self.path, f, destdir, 0)
                            if ans and ans != -100:
                                for panel in app.panels:
                                    panel.show()
                                messages.error('Copy \'%s\'' % f, '%s (%s)' % ans)
                        self.selections = []
                    else:
                        continue
                else:
                    filename = self.sorted[self.file_i]
                    if filename == os.pardir:
                        continue
                    buf = 'Copy \'%s\' to' % filename
                    destdir = doEntry('Copy', buf, destdir)
                    if destdir:
                        if app.prefs.confirmations['overwrite']:
                            ans = run_thread('Copying \'%s\'' % filename,
                                             files.copy,
                                             self.path, filename, destdir)
                            if type(ans) == type(''):
                                app.show()
                                ans2 = messages.confirm('Copy',
                                                        'Overwrite \'%s\'' %
                                                        ans, 1)
                                if ans2 != 0 and ans2 != -1:
                                    ans = run_thread('Copying \'%s\'' % filename,
                                                     files.copy,
                                                     self.path, filename, destdir, 0)
                                else:
                                    continue
                        else:
                            ans = run_thread('Copying \'%s\'' % filename,
                                             files.copy,
                                             self.path, filename, destdir, 0)
                        if ans and ans != -100:
                            for panel in app.panels:
                                panel.show()
                            messages.error('Copy \'%s\'' % filename,
                                           '%s (%s)' % ans)
                    else:
                        continue
                self.refresh_panel(self)
                self.refresh_panel(otherpanel)

            # move
            elif ch in [ord('m'), ord('M'), curses.KEY_F6]:
                otherpanel = app.get_otherpanel()
                destdir = otherpanel.path + os.sep
                if len(self.selections):
                    buf = 'Move %d items to' % len(self.selections)
                    destdir = doEntry('Move', buf, destdir)
                    if destdir:
                        overwrite_all = 0
                        for f in self.selections:
                            if not overwrite_all:
                                if app.prefs.confirmations['overwrite']:
                                    ans = run_thread('Moving \'%s\'' % f,
                                                     files.move,
                                                     self.path, f, destdir)
                                    if type(ans) == type(''):
                                        app.show()
                                        ans2 = messages.confirm_all('Move', 'Overwrite \'%s\'' % ans, 1)
                                        if ans2 == -1:
                                            break
                                        elif ans2 == 2:
                                            overwrite_all = 1
                                        if ans2 != 0:
                                            ans = run_thread('Moving \'%s\'' % f,
                                                             files.move,
                                                             self.path, f,
                                                             destdir, 0)
                                        else:
                                            continue
                                else:
                                    ans = run_thread('Moving \'%s\'' % f,
                                                     files.move,
                                                     self.path, f, destdir, 0)
                            else:
                                ans = run_thread('Moving \'%s\'' % f, files.move,
                                                 self.path, f, destdir, 0)
                            if ans and ans != -100:
                                for panel in app.panels:
                                    panel.show()
                                messages.error('Move \'%s\'' % f, '%s (%s)' % ans)
                        self.selections = []
                    else:
                        continue
                else:
                    filename = self.sorted[self.file_i]
                    if filename == os.pardir:
                        continue
                    buf = 'Move \'%s\' to' % filename
                    destdir = doEntry('Move', buf, destdir)
                    if destdir:
                        if app.prefs.confirmations['overwrite']:
                            ans = run_thread('Moving \'%s\'' % filename,
                                             files.move,
                                             self.path, filename, destdir)
                            if type(ans) == type(''):
                                app.show()
                                ans2 = messages.confirm('Move',
                                                        'Overwrite \'%s\'' %
                                                        ans, 1)
                                if ans2 != 0 and ans2 != -1:
                                    ans = run_thread('Moving \'%s\'' % filename,
                                                     files.move,
                                                     self.path, filename, destdir, 0)
                                else:
                                    continue
                        else:
                            ans = run_thread('Moving \'%s\'' % filename,
                                             files.move,
                                             self.path, filename, destdir, 0)
                        if ans and ans != -100:
                            for panel in app.panels:
                                panel.show()
                            messages.error('Move \'%s\'' % filename,
                                           '%s (%s)' % ans)
                            ans = files.move(self.path, filename, destdir, 0)
                    else:
                        continue
                self.refresh_panel(self)
                self.refresh_panel(otherpanel)

            # make directory
            elif ch in [curses.KEY_F7]:
                newdir = doEntry('Make directory', 'Type directory name')
                if newdir == None or newdir == "":
                    continue                      
                ans = files.mkdir(self.path, newdir)
                if ans:
                    for panel in app.panels:
                        panel.show()
                    messages.error('Make directory',
                                   '%s (%s)' % (ans, newdir))
                    continue
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())

            # delete
            elif ch in [ord('d'), ord('D'), curses.KEY_F8, curses.KEY_DC]:
                if len(self.selections):
                    delete_all = 0
                    for f in self.selections:
                        if f == os.pardir:
                            continue
                        buf = 'Delete \'%s\'' % f
                        if app.prefs.confirmations['delete'] and not delete_all:
                            ans2 = messages.confirm_all('Delete', buf, 1)
                            if ans2 == -1:
                                break
                            elif ans2 == 2:
                                delete_all = 1
                            if ans2 != 0:
                                ans = run_thread('Deleting \'%s\'' % f,
                                             files.delete, self.path, f)
                            else:
                                continue
                        else:
                            ans = run_thread('Deleting \'%s\'' % f,
                                             files.delete, self.path, f)
                        if ans and ans != -100:
                            for panel in app.panels:
                                panel.show()
                            messages.error('Delete \'%s\'' % f, '%s (%s)' % ans)
                        else:
                            continue

                    file_i_old = self.file_i
                    file_old = self.sorted[self.file_i]
                    self.init_dir(self.path)
                    try:
                        self.file_i = self.sorted.index(file_old)
                    except ValueError:
                        self.file_i = file_i_old

                else:
                    filename = self.sorted[self.file_i]
                    if filename == os.pardir:
                        continue
                    if app.prefs.confirmations['delete']:
                        ans2 = messages.confirm('Delete', 'Delete \'%s\'' %
                                                filename, 1)
                        if ans2 != 0 and ans2 != -1:
                            ans = run_thread('Deleting \'%s\'' % filename,
                                             files.delete, self.path, filename)
                        else:
                            continue
                    else:
                        ans = run_thread('Deleting \'%s\'' % filename,
                                         files.delete, self.path, filename)
                    if ans and ans != -100:
                        for panel in app.panels:
                            panel.show()
                        messages.error('Delete \'%s\'' % filename, '%s (%s)' % ans)

                    file_i_old = self.file_i
                    self.init_dir(self.path)
                    if file_i_old > self.nfiles:
                        self.file_i = self.nfiles
                    else:
                        self.file_i = file_i_old

                self.fix_limits()
                self.refresh_panel(app.get_otherpanel())

            # help
            elif ch in [ord('h'), ord('H'), curses.KEY_F1]:
                menu = [ 'r    Readme',
                         'v    Readme pyview',
                         'n    News',
                         't    Todo',
                         'c    ChangeLog',
                         'l    License' ]
                cmd = messages.MenuWin('Help Menu', menu).run()
                if cmd == -1:
                    continue
                cmd = cmd[0]
                curses.endwin()
                docdir = os.path.join(sys.exec_prefix, 'share/doc/lfm')
                if cmd == 'r':
                    fullfilename = os.path.join(docdir, 'README')
                elif cmd == 'v':
                    fullfilename = os.path.join(docdir, 'README.pyview')
                elif cmd == 'n':
                    fullfilename = os.path.join(docdir, 'NEWS')
                elif cmd == 't':
                    fullfilename = os.path.join(docdir, 'TODO')
                elif cmd == 'c':
                    fullfilename = os.path.join(docdir, 'ChangeLog')
                elif cmd == 'l':
                    fullfilename = os.path.join(docdir, 'COPYING')
                os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
                curses.curs_set(0)

            # file menu
            elif ch in [ord('f'), ord('F'), curses.KEY_F2]:
                menu = [ '@    Do something on file(s)',
                         'i    File info',
                         'p    Change file permissions, owner, group',
                         'g    Gzip/gunzip file(s)',
                         'b    Bzip2/bunzip2 file(s)',
                         'x    Uncompress .tar.gz, .tar.bz2, .tar.Z',
                         'c    Compress directory to .tar.gz',
                         'd    Compress directory to .tar.bz2',
                         'y    Encrypt/decrypt file' ]
                cmd = messages.MenuWin('File Menu', menu).run()
                if cmd == -1:
                    continue
                cmd = cmd[0]
                if cmd == '@':
                    app.show()
                    do_something_on_file(self)
                elif cmd == 'i':
                    do_show_file_info(self)
                elif cmd == 'p':
                    if self.selections:
                        app.show()
                        i = 0
                        change_all = 0
                        for file in self.selections:
                            i += 1
                            if not change_all:
                                ret = messages.ChangePerms(file, self.files[file],
                                                       app, i,
                                                       len(self.selections)).run()
                                if ret == -1:
                                    break
                                elif ret == 0:
                                    continue
                                elif ret[3] == 1:
                                    change_all = 1                            
                            filename = os.path.join(self.path, file)
                            ans = files.set_perms(filename, ret[0])
                            if ans:
                                app.show()
                                messages.error('Chmod', '%s (%s)' % (ans,
                                               filename))
                            ans = files.set_owner_group(filename, ret[1], ret[2])
                            if ans:
                                app.show()
                                messages.error('Chown', '%s (%s)' % (ans,
                                               filename))
                        self.selections = []
                    else:
                        file = self.sorted[self.file_i]
                        if file == os.pardir:
                            continue
                        app.show()
                        ret = messages.ChangePerms(file, self.files[file],
                                                   app).run()
                        if ret == -1:
                            continue
                        filename = os.path.join(self.path, file)
                        ans = files.set_perms(filename, ret[0])
                        if ans:
                            app.show()
                            messages.error('Chmod', '%s (%s)' % (ans, filename))
                        ans = files.set_owner_group(filename, ret[1], ret[2])
                        if ans:
                            app.show()
                            messages.error('Chown', '%s (%s)' % (ans, filename))
                    self.refresh_panel(self)
                    self.refresh_panel(app.get_otherpanel())
                elif cmd == 'g':
                    compress_uncompress_file(self, 'gzip')
                elif cmd == 'b':
                    compress_uncompress_file(self, 'bzip2')
                elif cmd == 'x':
                    uncompress_dir(self)
                    old_file = self.sorted[self.file_i]
                    self.refresh_panel(self)
                    self.file_i = self.sorted.index(old_file)
                    old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
                    self.refresh_panel(app.get_otherpanel())
                    app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
                elif cmd == 'c':
                    compress_dir(self, 'gzip')
                    old_file = self.sorted[self.file_i]
                    self.refresh_panel(self)
                    self.file_i = self.sorted.index(old_file)
                    old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
                    self.refresh_panel(app.get_otherpanel())
                    app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
                elif cmd == 'd':
                    compress_dir(self, 'bzip2')
                    old_file = self.sorted[self.file_i]
                    self.refresh_panel(self)
                    self.file_i = self.sorted.index(old_file)
                    old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
                    self.refresh_panel(app.get_otherpanel())
                    app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
                elif cmd == 'y':
                    app.show()
                    messages.notyet('Encrypt/decrypt file')

            # general menu
            elif ch in [curses.KEY_F9]:
                menu = [ '/    Find/grep file(s)',
                         '#    Show directories size',
                         's    Sort files',
                         't    Tree',
                         'f    Show filesystems info',
                         'o    Open shell',
                         'c    Edit configuration',
                         'a    Save configuration' ]
                cmd = messages.MenuWin('General Menu', menu).run()
                if cmd == -1:
                    continue
                cmd = cmd[0]
                if cmd == '/':
                    app.show()
                    findgrep(self)
                elif cmd == '#':
                    show_dirs_size(self)
                elif cmd == 's':
                    app.show()
                    sort(self)
                elif cmd == 't':
                    messages.notyet('Tree')
                elif cmd == 'f':
                    do_show_fs_info()
                elif cmd == 'o':
                    curses.endwin()
                    os.system('cd \"%s\"; %s' % (self.path,
                                                 app.prefs.progs['shell']))
                    curses.curs_set(0)
                    self.refresh_panel(self)
                    self.refresh_panel(app.get_otherpanel())
                elif cmd == 'c':
                    app.prefs.edit(app)
                    app.prefs.load()
                elif cmd == 'a':
                    app.prefs.save()

            # refresh screen
            elif ch in [0x12]:             # Ctrl-r
                app.show()
                self.refresh_panel(self)
                self.refresh_panel(app.get_otherpanel())

            # exit
            elif ch in [ord('q'), ord('Q'), curses.KEY_F10]:
                if app.prefs.confirmations['quit']:
                    ans = messages.confirm('Last File Manager',
                                           'Quit Last File Manager', 1)
                    if ans == 1:
                        return -1
                else:
                    return -1
            elif ch in [ord('x'), ord('X')]:
                if app.prefs.confirmations['quit']:
                    ans = messages.confirm('Last File Manager',
                                           'Quit Last File Manager', 1)
                    if ans == 1:
                        return -2
                else:
                    return -2

            # no more keys
            else:
                curses.beep()


##################################################
##### Actions
##################################################
import signal, tempfile, cPickle

# run thread: return -100 if stopped
def run_thread(title = 'Doing nothing', func = None, *args):
    """Run a function in background, so it can be stopped, continued, etc.
    There is also a graphical ad to show the program still runs and is not
    crashed. Returns nothing if all was ok, -100 if stoppped by user, or
    an error message."""
    
    global thread_quit

    def thread_quit_handler(signum, frame):
        global thread_quit
        thread_quit = 1
        
    app.win_status.erase()
    app.win_status.addstr(0, 1, title[:curses.COLS-22])
    app.win_status.addstr(0, curses.COLS - 21, 'Press Ctrl-C to stop')
    app.win_status.refresh()
    app.win_title.nodelay(1)
    filename = tempfile.mktemp()
    thread_quit = 0
    pid = os.getpid()
    signal.signal(signal.SIGUSR1, thread_quit_handler)
    thread_pid = os.fork()
    # error
    if thread_pid < 0:
        messages.error('Run Process', 'Can\'t execute process')
        return
    # child
    elif thread_pid == 0:
        res = func(*args)
        file = open(filename, 'w')
        cPickle.dump(res, file)
        file.close()
        os.kill(pid, signal.SIGUSR1)
        os._exit(0)
    # parent
    while not thread_quit:
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
                app.win_status.erase()
                app.win_status.addstr(0, 1, title[:curses.COLS-22])
                app.win_status.addstr(0, curses.COLS - 21, 'Press Ctrl-C to stop')
                app.win_status.refresh()
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
    os.wait()
    file = open(filename, 'r')
    res = cPickle.load(file)
    file.close()
    os.unlink(filename)
    return res


# do special view file
def do_special_view_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    ext = os.path.splitext(fullfilename)[1].lower()[1:]
    for type, exts in filetypes.items():
        if ext in exts:
            sys.stdout = sys.stderr = '/dev/null'
            curses.endwin()
            pid = os.fork()
            if pid == 0:
                args = app.prefs.progs[type].split()
                args.append(fullfilename)
                os.execvp(args[0], args)
            else:
                time.sleep(2)
                curses.curs_set(0)
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                break
    else:
        do_view_file(panel)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# do view file
def do_view_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    curses.endwin()
    os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
    curses.curs_set(0)


# do edit file
def do_edit_file(panel):
    curses.endwin()
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    os.system('%s \"%s\"' % (app.prefs.progs['editor'], fullfilename))
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# do execute file
def do_do_execute_file(path, cmd):
    i, a = os.popen4('cd \"%s\"; %s; echo ZZENDZZ' % (path, cmd))
    output = ''
    while 1:
        buf = a.readline()[:-1]
        if buf == 'ZZENDZZ':
            break
        elif buf:
            output += buf + '\n'
    i.close(); a.close()
    return output


def do_execute_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    parms = doEntry('Execute file', 'Enter arguments')
    if parms == None:
        return
    elif parms == '':
        cmd = '\"%s\"' % fullfilename
    else:                
        cmd = '%s %s' % (fullfilename, parms)
    curses.endwin()
    err = run_thread('Executing \"%s\"' % cmd, do_do_execute_file, panel.path, cmd)
    if err and err != -100:
        if app.prefs.options['show_output_after_exec']:
            curses.curs_set(0)
            for panel in app.panels:
                panel.show()
            if messages.confirm('Executing file(s)', 'Show output'):
                lst = [(l, 2) for l in err.split('\n')]
                pyview.InternalView('Output of \"%s\"' % cmd,
                                    lst, center = 0).run()
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


##### File Menu
# do something on file

### do_something_on_file does not have to run inside run_thread, either capture
### the output because it makes not possible to exec commands such as 'less', etc.

# def do_do_something_on_file(panel, cmd, filename):
#     i, a = os.popen4('cd \"%s\"; %s \"%s\"; echo ZZENDZZ' %
#                      (panel.path, cmd, filename))
#     output = ''
#     while 1:
#         buf = a.readline()[:-1]
#         if buf == 'ZZENDZZ':
#             break
#         elif buf:
#             output += buf + '\n'
#     i.close(); a.close()
#     return output


# def do_something_on_file(panel):
#     cmd = doEntry('Do something on file(s)', 'Enter command')
#     if cmd:
#         curses.endwin()
#         if len(panel.selections):
#             for f in panel.selections:
#                 err = run_thread('Executing \"%s %s\"' % (cmd, f),
#                                  do_do_something_on_file, panel, cmd, f)
#                 if err and err != -100:
#                     if app.prefs.options['show_output_after_exec']:
#                         curses.curs_set(0)
#                         for panel in app.panels:
#                             panel.show()
#                         if messages.confirm('Do something on file(s)',
#                                             'Show output'):
#                             lst = [(l, 2) for l in err.split('\n')]
#                             pyview.InternalView('Output of \"%s %s\"' %
#                                                 (cmd, f),
#                                                 lst, center = 0).run()
#             panel.selections = []
#         else:
#             filename = panel.sorted[panel.file_i]
#             err = run_thread('Executing \"%s %s\"' % (cmd, filename),
#                              do_do_something_on_file, panel, cmd, filename)
#             if err and err != -100:
#                 if app.prefs.options['show_output_after_exec']:
#                     curses.curs_set(0)
#                     for panel in app.panels:
#                         panel.show()
#                     if messages.confirm('Do something on file(s)', 'Show output'):
#                         lst = [(l, 2) for l in err.split('\n')]
#                         pyview.InternalView('Output of \"%s %s\"' %
#                                             (cmd, filename),
#                                             lst, center = 0).run()
#         curses.curs_set(0)
#         panel.refresh_panel(panel)
#         panel.refresh_panel(app.get_otherpanel())


def do_something_on_file(panel):
    cmd = doEntry('Do something on file(s)', 'Enter command')
    if cmd:
        curses.endwin()
        if len(panel.selections):
            for f in panel.selections:
                os.system('cd \"%s\"; %s \"%s\"' % (panel.path, cmd, f))
            panel.selections = []
        else:
            os.system('cd \"%s\"; %s \"%s\"' %
                      (panel.path, cmd, panel.sorted[panel.file_i]))
        curses.curs_set(0)
        panel.refresh_panel(panel)
        panel.refresh_panel(app.get_otherpanel())


# compress/uncompress file: gzip/gunzip, bzip2/bunzip2
def do_compress_uncompress_file(comp, prog, file, fullfile):
    if prog == 'gzip':
        ext = '.gz'
    else:
        ext = '.bz2'
    if len(file) > len(ext) and file[-len(ext):] == ext:
        i, a = os.popen4('%s -d %s' % (comp, fullfile))
    else:
        i, a = os.popen4('%s %s' % (comp, fullfile))
    err = a.read()
    i.close(); a.close()
    return err


def compress_uncompress_file(panel, prog):
    comp = app.prefs.progs[prog]
    if comp == '':
        app.show()
        messages.error(prog, 'No %s program found in path' % prog)
        return
    if panel.selections:
        for file in panel.selections:
            fullfile = os.path.join(panel.path, file)
            if not os.path.isfile(fullfile):
                app.show()
                messages.error(comp, '%s: Can\'t un/compress' % file)
                continue
            err = run_thread('Un/Compressing \'%s\'' % file,
                             do_compress_uncompress_file,
                             comp, prog, file, fullfile)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error un/compressing \'%s\'' % file, err.strip())
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
        err = run_thread('Un/Compressing \'%s\'' % file,
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
def check_compressed_tarfile(file):
    """check if correct compressed and tarred file, if so returns compress
    program"""
    
    if (len(file) > 7 and file[-7:] == '.tar.gz') or \
       (len(file) > 4 and file[-4:] == '.tgz') or \
       (len(file) > 6 and file[-6:] == '.tar.Z'):
        return app.prefs.progs['gzip']
    elif (len(file) > 8 and file[-8:] == '.tar.bz2'):
        return app.prefs.progs['bzip2']
    else:
        return -1


def do_uncompress_dir(path, comp, file):
    i, oe = os.popen4('cd \"%s\"; %s -d %s -c | %s xf -; echo ZZENDZZ' %
                      (path, comp, file, app.prefs.progs['tar']))
    while 1:
        buf = oe.read()[:-1]
        if buf == 'ZZENDZZ':
            i.close(); oe.close()
            return
        else:
            i.close(); oe.close()
            buf = buf.replace('ZZENDZZ', '')
            return buf

    
def uncompress_dir(panel):
    """uncompress tarred file to current directory"""
    
    if app.prefs.progs['tar'] == '':
        app.show()
        messages.error('Uncompress directory', 'No tar program found in path')
        return
    if panel.selections:
        for file in panel.selections:
            comp = check_compressed_tarfile(file)
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
            err = run_thread('Uncompressing file \'%s\'' % file, do_uncompress_dir,
                             panel.path, comp, file)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error uncompressing \'%s\'' % file, err)
        panel.selections = []
    else:
        file = panel.sorted[panel.file_i]
        comp = check_compressed_tarfile(file)
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
        err = run_thread('Uncompressing file \'%s\'' % file, do_uncompress_dir,
                         panel.path, comp, file)
        if err and err != -100:
            for panel in app.panels:
                panel.show()
            messages.error('Error uncompressing \'%s\'' % file, err)


# compress directory: tar and gzip, bzip2
def do_compress_dir(path, prog, file, ext):
    tmpfile = tempfile.mktemp()
    i, oe = os.popen4('cd \"%s\"; %s cf - %s | %s >%s; echo ZZENDZZ' %
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
    try:
        files.do_copy(tmpfile, os.path.join('%s' % path,
                                            '%s.tar.%s' % (file, ext)))
    except (IOError, os.error), (errno, strerror):
        os.unlink(tmpfile)
        return '%s (%s)' % (strerror, errno)
    os.unlink(tmpfile)


def compress_dir(panel, prog):
    """compress directory to current path"""

    if app.prefs.progs['tar'] == '':
        app.show()
        messages.error('Compress directory', 'No tar program found in path')
        return
    if app.prefs.progs[prog] == '':
        app.show()
        messages.error('Compress directory', 'No %s program found in path' % prog)
        return
    if prog == 'gzip':
        ext = 'gz'
    else:
        ext = 'bz2'
    if panel.selections:
        for file in panel.selections:
            if not os.path.isdir(os.path.join(panel.path, file)):
                app.show()
                messages.error('Compress directory',
                               '%s: is not a directory' % file)
                continue

            err = run_thread('Compressing directory \'%s\'' % file,
                             do_compress_dir,
                             panel.path, prog, file, ext)
            if err and err != -100:
                for panel in app.panels:
                    panel.show()
                messages.error('Error compressing \'%s\'' % file, err)
        panel.selections = []
    else:
        file = panel.sorted[panel.file_i]
        if not os.path.isdir(os.path.join(panel.path, file)):
            app.show()
            messages.error('Compress directory',
                           '%s: is not a directory' % file)
            return
        err = run_thread('Compressing directory \'%s\'' % file, do_compress_dir,
                         panel.path, prog, file, ext)
        if err and err != -100:
            for panel in app.panels:
                panel.show()
            messages.error('Error compressing \'%s\'' % file, err)


# show file info
def do_show_file_info(panel):
    def show_info(panel, file):
        import stat
        from time import ctime

        fullfilename = os.path.join(panel.path, file)
        file_data = panel.files[file]
        file_data2 = os.lstat(fullfilename)
        buf = []
        user = os.environ['USER']
        username = files.get_user_fullname(user)
        so, host, ver, tmp, arch = os.uname()
        buf.append(('%s v%s executed by %s' % (PROGNAME, VERSION, username), 5))
        buf.append(('<%s@%s> on a %s %s [%s]' % (user, host, so, ver, arch), 5))
        buf.append(('', 2))
        fileinfo = os.popen('file \"%s\"' % \
                            fullfilename).read().split(':')[1].strip()
        buf.append(('%s: %s (%s)' % (files.FILETYPES[file_data[0]][1], file,
                                     fileinfo), 6))
        buf.append(('Path: %s' % panel.path[:curses.COLS-8], 6))
        buf.append(('Size: %s bytes' % file_data[files.FT_SIZE], 6))
        buf.append(('Mode: %s (%4.4o)' % \
                    (files.perms2str(file_data[files.FT_PERMS]),
                     file_data[files.FT_PERMS]), 6))
        buf.append(('Links: %s' % file_data2[stat.ST_NLINK], 6))
        buf.append(('User ID: %s (%s) / Group ID: %s (%s)' % \
                    (file_data[files.FT_OWNER], file_data2[stat.ST_UID],
                     file_data[files.FT_GROUP], file_data2[stat.ST_GID]), 6))
        buf.append(('Last access: %s' % ctime(file_data2[stat.ST_ATIME]), 6))
        buf.append(('Last modification: %s' % ctime(file_data2[stat.ST_MTIME]), 6))
        buf.append(('Last change: %s' % ctime(file_data2[stat.ST_CTIME]), 6))
        buf.append(('Location: %d, %d / Inode: #%X (%Xh:%Xh)' % \
                    ((file_data2[stat.ST_DEV] >> 8) & 0x00FF,
                    file_data2[stat.ST_DEV] & 0x00FF,
                    file_data2[stat.ST_INO], file_data2[stat.ST_DEV],
                    file_data2[stat.ST_INO]), 6))
        fss = files.get_fs_info()
        fs = ['/dev', '0', '0', '0', '0%', '/', 'unknown']
        for e in fss:
            if fullfilename.find(e[5]) != -1 and (len(e[5]) > len(fs[5]) or e[5] == os.sep):
                fs = e
        buf.append(('File system: %s on %s (%s) %d%% free' % \
                    (fs[0], fs[5], fs[6], 100 - int(fs[4][:-1])), 6))
        pyview.InternalView('Information about \'%s\'' % file, buf).run()


    if panel.selections:
        for f in panel.selections:
            show_info(panel, f)
        panel.selections = []
    else:
        show_info(panel, panel.sorted[panel.file_i])
    

##### General Menu
# show directories size
def show_dirs_size(panel):
    if panel.selections:
        for f in panel.selections:
            if panel.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
               panel.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                continue
            file = os.path.join(panel.path, f)
            res = run_thread('Showing Directories Size',
                             files.get_fileinfo, file, 0, 1)
            if res == -100:
                break
            panel.files[f] = res
                                               
    else:
        for f in panel.files.keys():
            if f == os.pardir:
                continue
            if panel.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
               panel.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                continue
            file = os.path.join(panel.path, f)
            res = run_thread('Showing Directories Size',
                             files.get_fileinfo, file, 0, 1)
            if res == -100:
                break
            panel.files[f] = res


# find and grep
def findgrep(panel):
    fs, pat = doDoubleEntry('Find files', 'Filename', '*', 1, 1,
                            'Content', '', 1, 0)
    if fs == None or fs == '':
        return
    path = os.path.dirname(fs)
    fs = os.path.basename(fs)
    if path == None or path == '':
        path = panel.path
    if path[0] != os.sep:
        path = os.path.join(panel.path, path)
    if pat:
        m = run_thread('Searching for \'%s\' in \"%s\" files' % (pat, fs),
                       files.findgrep,
                       path, fs, pat, app.prefs.progs['find'],
                       app.prefs.progs['egrep'])
        if not m:
            app.show()
            messages.error('Find/Grep', 'No files found')
            return
        elif m == -100:
            return
        elif m == -1:
            app.show()
            messages.error('Find/Grep', 'Error while creating pipe')
            return
    else:
        m = run_thread('Searching for \"%s\" files' % fs, files.find,
                       path, fs, app.prefs.progs['find'])
        if not m:
            app.show()
            messages.error('Find', 'No files found')
            return
        elif m == -100:
            return
        elif m == -1:
            app.show()
            messages.error('Find', 'Error while creating pipe')
            return        
    find_quit = 0
    par = ''
    while not find_quit:
        cmd, par = messages.FindfilesWin(m, par).run()
        if par:
            par2 = par.split(':')
            if len(par2) == 2:
                try:
                    line = int(par2[0])
                except ValueError:
                    line = 0
                    f = os.path.join(path, par)
                else:
                    f = os.path.join(path, par2[1])
            else:
                line = 0
                f = os.path.join(path, par)
            if os.path.isdir(f):
                todir = f
                tofile = None
            else:
                todir = os.path.dirname(f)
                tofile = os.path.basename(f)
        if cmd == 0:             # goto file
            panel.init_dir(todir)
            if tofile:
                panel.file_i = panel.sorted.index(tofile)
            panel.fix_limits()
            find_quit = 1
        elif cmd == 1:
            messages.notyet('Panelize')
        elif cmd == 2:           # view
            if tofile:
                curses.curs_set(0)
                curses.endwin()
                os.system('%s +%d \"%s\"' %
                          (app.prefs.progs['pager'], line, f))
                curses.curs_set(0)
            else:
                messages.error('View', 'it\'s a directory',
                               todir)
        elif cmd == 3:           # edit
            if tofile:
                curses.endwin()
                if line > 0:
                    os.system('%s +%d \"%s\"' %
                              (app.prefs.progs['editor'], line, f))
                else:
                    os.system('%s \"%s\"' %
                              (app.prefs.progs['editor'], f))
                curses.curs_set(0)
                panel.refresh_panel(panel)
                panel.refresh_panel(app.get_otherpanel())
            else:
                messages.error('Edit', 'it\'s a directory',
                               todir)
        elif cmd == 4:           # do something on file
            cmd2 = doEntry('Do something on file',
                           'Enter command')
            if cmd2:
                curses.endwin()
                os.system('%s \"%s\"' % (cmd2, f))
                curses.curs_set(0)
                panel.refresh_panel(panel)
                panel.refresh_panel(app.get_otherpanel())
        else:
            find_quit = 1


# sort
def sort(panel):
    while 1:
        ch = messages.get_a_key('Sorting mode',
                                'N(o), by (n)ame, by (s)ize, by (d)ate,\nuppercase if reversed order, Ctrl-C to quit')
        if ch in [ord('o'), ord('O')]:
            app.modes['sort'] = files.SORTTYPE_None
            break
        elif ch in [ord('n')]:
            app.modes['sort'] =  files.SORTTYPE_byName
            break
        elif ch in [ord('N')]:
            app.modes['sort'] =  files.SORTTYPE_byName_rev
            break
        elif ch in [ord('s')]:
            app.modes['sort'] = files.SORTTYPE_bySize
            break
        elif ch in [ord('S')]:
            app.modes['sort'] = files.SORTTYPE_bySize_rev
            break
        elif ch in [ord('d')]:
            app.modes['sort'] = files.SORTTYPE_byDate
            break
        elif ch in [ord('D')]:
            app.modes['sort'] = files.SORTTYPE_byDate_rev
            break
        elif ch == -1:                 # Ctrl-C
            break
    old_filename = panel.sorted[panel.file_i]
    old_selections = panel.selections[:]
    panel.init_dir(panel.path)
    panel.file_i = panel.sorted.index(old_filename)
    panel.selections = old_selections 


# do show filesystems info
def do_show_fs_info():
    """Show file systems info"""

    fs = files.get_fs_info()
    if type(fs) != type([]):
        app.show()
        messages.error('Show filesystems info', fs)
        return
    app.show()
    buf = []
    buf.append(('Filesystem       FS type    Total Mb     Used   Avail.  Use%  Mount point', 6))
    buf.append('-')
    for l in fs:
        buf.append(('%-15s  %-10s  %7s  %7s  %7s  %4s  %s' % \
                    (l[0], l[6], l[1], l[2], l[3], l[4], l[5]), 2))
    texts = [l[0] for l in buf]
    buf[1] = ('-' * len(max(texts)), 6)
    pyview.InternalView('Show filesystems info', buf).run()


##################################################
##### Wrappers
##################################################
def doEntry(title, help, path = '', with_historic = 1, with_complete = 1):
    panelpath = app.panels[app.panel].path
    while 1:
        path = messages.Entry(title, help, path, with_historic, with_complete,
                              panelpath).run()
        if type(path) != type([]):
            return path
        else:
            app.show()
            path = path.pop()


def doDoubleEntry(title, help1, path1 = '', with_historic1 = 1, with_complete1 = 1,
                  help2 = '', path2 = '', with_historic2 = 1, with_complete2 = 1):
    active_entry = 0
    panelpath1 = app.panels[app.panel].path
    panelpath2 = app.panels[app.panel].path
    while 1:
        path = messages.DoubleEntry(title, help1, path1, with_historic1,
                                    with_complete1, panelpath1,
                                    help2, path2, with_historic2,
                                    with_complete2, panelpath2,
                                    active_entry).run()
        if type(path) != type([]):
            return path
        else:
            app.show()
            active_entry = path.pop()
            path2 = path.pop()
            path1 = path.pop()


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
""" % (PROGNAME, VERSION, DATE, AUTHOR, prog)


def main(win, path, npanels):
    global app

    app = Lfm(path, npanels)
    if app == OSError:
        sys.exit(-1)
    return app.run()

    
if __name__ == '__main__':
    import getopt

    # defaults
    npanels = 2
    paths = []
   
    # args
    try:
        opts, args = getopt.getopt(sys.argv[1:], '12dh',
                                   ['', '', 'debug', 'help'])
    except getopt.GetoptError:
        usage(sys.argv[0], 'Bad argument(s)')
        sys.exit(-1)
    for o, a in opts:
        if o == '-1':
            npanels = 1
        if o == '-2':
            npanels = 2
        if o in ('-d', '--debug'):
            DEBUG = 1
        if o in ('-h', '--help'):
            usage(sys.argv[0])
            sys.exit(2)

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
                usage(sys.argv[0], '<%s> is not a file or directory' % args[0])
                sys.exit(-1)
        paths.append(buf)
        paths.append(os.path.abspath('.'))
    elif len(args) == 2:
        buf = os.path.abspath(args[0])
        if not os.path.isdir(buf):
            usage(sys.argv[0], '<%s> is not a file or directory' % args[0])
            sys.exit(-1)
        paths.append(buf)
        buf = os.path.abspath(args[1])
        if not os.path.isdir(buf):
            usage(sys.argv[0], '<%s> is not a file or directory' % args[1])
            sys.exit(-1)
        paths.append(buf)
    else:
        usage(sys.argv[0], 'Incorrect number of arguments')
        sys.exit(-1)

    DEBUGFILE = "./lfm-log.%d" % os.getpid()
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
    if path:
        f = open('/tmp/lfm-%s.path' % (os.getppid()), 'w')
        f.write(path)
        f.close()
