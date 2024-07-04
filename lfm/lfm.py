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


import os, os.path
import sys, popen2
import curses
from glob import glob

from lfm import files
from lfm import messages
#import files
#import messages


PROGNAME = 'lfm - Last File Manager'
VERSION = '0.4'
DATE = '2001'
AUTHOR = 'Iñigo Serna'

DEBUG = 0


##################################################
##################################################
app = None


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
        self.prefs = Preferences()
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

        while 1:
            self.show()
            oldpanel = self.panels[self.panel].manage_keys()
            if oldpanel == -1:
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
        self.__init_dir(path, app)


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
    def __init_dir(self, path, application = None):
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
            self.__fix_limits()
            self.path = os.path.abspath(path)
            self.selections = []
        except OSError, (errno, strerror):
            messages.error('Enter In Directory', '%s (%d)' %
                           (strerror, errno), path)
            app.show()
            return OSError


    def __fix_limits(self):
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


    def __refresh_panel(self, panel):
        """this is needed due to panel could be changed"""

        filename_old = panel.sorted[panel.file_i]
        selections_old = panel.selections[:]
        panel.__init_dir(panel.path)
        try:
            panel.file_i = panel.sorted.index(filename_old)
        except ValueError:
            panel.file_i = 0
        panel.__fix_limits()
        panel.selections = selections_old[:]
        for f in panel.selections:
            if f not in panel.sorted:
                panel.selections.remove(f)


    # Keys
    def manage_keys(self):
        while 1:
            app.show()
            ch = self.win_files.getch()
#              print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                    (curses.keyname(ch), ch & 255, ch, ch)
#              messages.win('Keyboard hitted:',
#                           'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                           (curses.keyname(ch), ch & 255, ch, ch))


            # to avoid extra chars input
            if ch == 0x1B:
                ch = self.win_files.getch()

            # cursor up
            if ch in [ord('p'), ord('P'), curses.KEY_UP]:
                self.file_i -= 1
                self.__fix_limits()
            # cursor down
            elif ch in [ord('n'), ord('N'), curses.KEY_DOWN]:
                self.file_i += 1
                self.__fix_limits()
            # page previous
            elif ch in [curses.KEY_PPAGE, curses.KEY_BACKSPACE,
                        0x08, 0x10]:                         # BackSpace, Ctrl-P
                self.file_i -= self.dims[0]
                if self.pos == 1 or self.pos == 2:
                    self.file_i += 3
                self.__fix_limits()
            # page next
            elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:   # Ctrl-N
                self.file_i += self.dims[0]
                if self.pos == 1 or self.pos == 2:
                    self.file_i -= 3
                self.__fix_limits()
            # home
            elif ch in [curses.KEY_HOME, 72, 348]:
                self.file_i = 0
                self.__fix_limits()
            # end
            elif ch in [curses.KEY_END, 70, 351]:
                self.file_i = self.nfiles - 1
                self.__fix_limits()
            
            # cursor left
            elif ch in [curses.KEY_LEFT]:
                if self.path != os.sep:
                    olddir = os.path.basename(self.path)
                    self.__init_dir(os.path.dirname(self.path))
                    self.file_i = self.sorted.index(olddir)
                    self.__fix_limits()
            # cursor right
            elif ch in [curses.KEY_RIGHT]:
                filename = self.sorted[self.file_i]
                if self.files[filename][files.FT_TYPE] == files.FTYPE_DIR:
                    self.__init_dir(os.path.join(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
                    self.__init_dir(files.get_linkpath(self.path, filename))
                else:
                    continue
            # go to directory
            elif ch in [ord('g'), ord('G')]:
                todir = doEntry('Go to directory', 'Type directory name')
                app.show()
                if todir == None or todir == "":
                    continue
                todir = os.path.join(self.path, todir)
                self.__init_dir(todir)
                self.__fix_limits()
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
                self.__fix_limits()

            # go to bookmark
            elif 0x30 <= ch <= 0x39:       # 0..9
                todir = app.prefs.bookmarks[ch - 0x30];
                self.__init_dir(todir)
                self.__fix_limits()
            # set bookmark
            elif ch in [ord('b')]:
                while 1:
                    ch = messages.get_a_key('Set bookmark',
                                            'Press 0-9 to save the bookmark in, Ctrl-C to quit')
                    if 0x30 <= ch <= 0x39:         # 0..9
                        app.prefs.bookmarks[ch-0x30] = self.path[:]
                        break
                    elif ch == -1:                 # Ctrl-C
                        break
            # edit bookmarks
            elif ch in [ord('B')]:
                messages.notyet('Edit bookmarks')

            # show directories size
            elif ch in [ord('#')]:
                if self.selections:
                    for f in self.selections:
                        if self.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
                           self.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                            continue
                        file = os.path.join(self.path, f)
                        self.files[f] = files.get_fileinfo(file,
                                                           show_dirs_size = 1)
                else:
                    for f in self.files.keys():
                        if f == os.pardir:
                            continue
                        if self.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
                           self.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                            continue
                        file = os.path.join(self.path, f)
                        self.files[f] = files.get_fileinfo(file,
                                                           show_dirs_size = 1)
            # sorting mode
            elif ch in [ord('s'), ord('S')]:
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
                old_filename = self.sorted[self.file_i]
                old_selections = self.selections[:]
                self.__init_dir(self.path)
                self.file_i = self.sorted.index(old_filename)
                self.selections = old_selections 
            
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
                self.__fix_limits()
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
                otherpanel.__init_dir(self.path)
                otherpanel.__fix_limits()
                
            # select item
            elif ch in [curses.KEY_IC]:
                filename = self.sorted[self.file_i]
                if filename == os.pardir:
                    self.file_i += 1
                    self.__fix_limits()
                    continue
                try:
                    self.selections.index(filename)
                except ValueError:
                    self.selections.append(filename)
                else:
                    self.selections.remove(filename)
                self.file_i += 1
                self.__fix_limits()
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
                        self.__init_dir(os.path.dirname(self.path))
                        self.file_i = self.sorted.index(olddir)
                        self.__fix_limits()
                    else:
                        self.__init_dir(os.path.join(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
                    self.__init_dir(files.get_linkpath(self.path, filename))
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_EXE:
                    curses.endwin()
                    os.system(os.path.join(self.path,
                                           self.sorted[self.file_i]))
                    curses.curs_set(0)
                    self.__refresh_panel(self)
                    self.__refresh_panel(app.get_otherpanel())
                elif self.files[filename][files.FT_TYPE] == files.FTYPE_REG:
                    curses.endwin()
                    fullfilename = os.path.join(self.path, self.sorted[self.file_i])
                    os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
                    curses.curs_set(0)
                else:
                    continue

            # do something on file
            elif ch in [ord('@')]:
                cmd = doEntry('Do something on file(s)', 'Enter command')
                if cmd:
                    curses.endwin()
                    if len(self.selections):
                        for f in self.selections:
                            fullfilename = os.path.join(self.path, f)
                            os.system('%s \"%s\"' % (cmd, fullfilename))
                        self.selections = []
                    else:
                        fullfilename = os.path.join(self.path,
                                                    self.sorted[self.file_i])
                        os.system('%s \"%s\"' % (cmd, fullfilename))
                    curses.curs_set(0)
                    self.__refresh_panel(self)
                    self.__refresh_panel(app.get_otherpanel())

            # special regards
            elif ch in [0xF1]:
                messages.win('Special Regards',
                             '  Maite zaitut, Montse\n   T\'estimo molt, Montse')
            # find/grep
            elif ch in [ord('/')]:
                fs, pat = doDoubleEntry('Find files', 'Filename', '*', 1, 1,
                                        'Content', '', 1, 0)

            # touch file
            elif ch in [ord('t'), ord('T')]:
                newfile = doEntry('Touch file', 'Type file name')
                if newfile == None or newfile == "":
                    continue                      
                fullfilename = os.path.join(self.path, newfile)
                err, a = popen2.popen4('touch \"%s\"' % fullfilename)
                err = err.read().split(':')[-1:][0].strip()
                if err:
                    app.show()
                    messages.error('Touch file', '%s: %s' % (newfile, err))
                curses.curs_set(0)
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())
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
                    messages.error('Edit link', '%s (%s)' % ans,
                                   self.sorted[self.file_i])
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())
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
                        messages.error('Edit link', '%s (%s)' % ans,
                                       self.sorted[self.file_i])
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())

            # shell
            elif ch in [0x0F]:             # Ctrl-O
                curses.endwin()
                os.system('cd \"%s\"; %s' % (self.path,
                                             app.prefs.progs['shell']))
                curses.curs_set(0)
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())
            # view
            elif ch in [ord('v'), ord('V'), curses.KEY_F3]:
                curses.endwin()
                fullfilename = os.path.join(self.path, self.sorted[self.file_i])
                os.system('%s \"%s\"' % (app.prefs.progs['pager'],
                                         fullfilename))
                curses.curs_set(0)
            # edit
            elif ch in [ord('e'), ord('E'), curses.KEY_F4]:
                curses.endwin()
                fullfilename = os.path.join(self.path, self.sorted[self.file_i])
                os.system('%s \"%s\"' % (app.prefs.progs['editor'],
                                         fullfilename))
                curses.curs_set(0)
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())

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
                                    ans = files.copy(self.path, f, destdir)
                                    if type(ans) == type(''):
                                        app.show()
                                        ans2 = messages.confirm_all('Copy', 'Overwrite \'%s\'' % ans, 1)
                                        if ans2 == -1:
                                            break
                                        elif ans2 == 2:
                                            overwrite_all = 1
                                        if ans2 != 0:
                                            ans = files.copy(self.path, f,
                                                             destdir, 0)
                                        else:
                                            continue
                                else:
                                    ans = files.copy(self.path, f, destdir, 0)
                            else:
                                ans = files.copy(self.path, f, destdir, 0)
                            if ans:
                                app.show()
                                messages.error('Copy', '%s (%s)' % ans, f)
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
                            ans = files.copy(self.path, filename, destdir)
                            if type(ans) == type(''):
                                app.show()
                                ans2 = messages.confirm('Copy',
                                                        'Overwrite \'%s\'' %
                                                        ans, 1)
                                if ans2 != 0 and ans2 != -1:
                                    ans = files.copy(self.path, filename,
                                                     destdir, 0)
                                else:
                                    continue
                        else:
                            ans = files.copy(self.path, filename, destdir, 0)
                        if ans:
                            app.show()
                            messages.error('Copy', '%s (%s)' % ans, filename)
                    else:
                        continue
                self.__refresh_panel(self)
                self.__refresh_panel(otherpanel)

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
                                    ans = files.move(self.path, f, destdir)
                                    if type(ans) == type(''):
                                        app.show()
                                        ans2 = messages.confirm_all('Move', 'Overwrite \'%s\'' % ans, 1)
                                        if ans2 == -1:
                                            break
                                        elif ans2 == 2:
                                            overwrite_all = 1
                                        if ans2 != 0:
                                            ans = files.move(self.path, f,
                                                             destdir, 0)
                                        else:
                                            continue
                                else:
                                    ans = files.move(self.path, f, destdir, 0)
                            else:
                                ans = files.move(self.path, f, destdir, 0)
                            if ans:
                                app.show()
                                messages.error('Move',
                                               '%s (%s)' % ans, filename)
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
                            ans = files.move(self.path, filename, destdir)
                            if type(ans) == type(''):
                                app.show()
                                ans2 = messages.confirm('Move',
                                                        'Overwrite \'%s\'' %
                                                        ans, 1)
                                if ans2 != 0 and ans2 != -1:
                                    ans = files.move(self.path, filename,
                                                     destdir, 0)
                                else:
                                    continue
                        else:
                            ans = files.move(self.path, filename, destdir, 0)
                        if ans:
                            app.show()
                            messages.error('Move', '%s (%s)' % ans, filename)
                    else:
                        continue
                self.__refresh_panel(self)
                self.__refresh_panel(otherpanel)

            # make directory
            elif ch in [curses.KEY_F7]:
                newdir = doEntry('Make directory', 'Type directory name')
                if newdir == None or newdir == "":
                    continue                      
                ans = files.mkdir(self.path, newdir)
                if ans:
                    messages.error('Make directory',
                                   '%s (%s)' % ans, newdir)
                    continue
                self.__refresh_panel(self)
                self.__refresh_panel(app.get_otherpanel())

            # delete
            elif ch in [ord('d'), ord('D'), curses.KEY_F8, curses.KEY_DC]:
                file_i_old = self.file_i
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
                                ans = files.delete(self.path, f)
                            else:
                                continue
                        else:
                            ans = files.delete(self.path, f)
                        if ans:
                            app.show()
                            messages.error('Delete', '%s (%s)' % ans, f)
                        else:
                            continue
                else:
                    filename = self.sorted[self.file_i]
                    if filename == os.pardir:
                        continue
                    if app.prefs.confirmations['delete']:
                        ans2 = messages.confirm('Delete', 'Delete \'%s\'' %
                                                filename, 1)
                        if ans2 != 0 and ans2 != -1:
                            ans = files.delete(self.path, filename)
                        else:
                            continue
                    else:
                            ans = files.delete(self.path, filename)
                    if ans:
                        app.show()
                        messages.error('Delete', '%s (%s)' % ans, filename)
                self.__init_dir(self.path)
                if file_i_old > self.nfiles:
                    self.file_i = self.nfiles
                else:
                    self.file_i = file_i_old
                self.__fix_limits()
                self.__refresh_panel(app.get_otherpanel())

            # help
            elif ch in [ord('h'), ord('H'), curses.KEY_F1]:
                messages.notyet('Help')

            # file menu
            elif ch in [ord('f'), ord('F'), curses.KEY_F2]:
                messages.notyet('File Menu')

            # general menu
            elif ch in [curses.KEY_F9]:
                messages.notyet('General Menu')

            # refresh screen
            elif ch in [0x12]:             # Ctrl-r
                app.show()

            # exit
            elif ch in [ord('x'), ord('X'), ord('q'), ord('Q'), curses.KEY_F10]:
                return -1

            # no more keys
            else:
                curses.beep()


##################################################
##### preferences
##################################################
class Preferences:
    """Preferences class"""
    
    def __init__(self):
        # default preferences
        self.progs = { 'shell':'bash', 'pager':'biew', 'editor':'mcedit' }
        self.bookmarks = [ '/',
                           '/home/inigo',
                           '/home/inigo/personal',
                           '/home/inigo/devel/mine/lfm',
                           '/zzz/compiling/gnome',
                           '/zzz/compiling/python',
                           '/zzz/compiling/linux',
                           '/etc',
                           '/root',
                           '/dfsdf' ]
        self.modes = { 'sort': files.SORTTYPE_byName,
                       'sort_mix_dirs': 0, 'sort_mix_cases': 0 }
        self.confirmations = { 'delete': 1, 'overwrite': 1 }


##################################################
##################################################
def doEntry(title, help, path = '', with_historic = 1, with_complete = 1):
    curpath = app.panels[app.panel].path
    while 1:
        if with_complete:
            if not path or path == '':
                basepath = app.panels[app.panel].path
            elif path[0] == os.sep:
                basepath = path[:]
            else:
                basepath = app.panels[app.panel].path
        else:
            basepath = ''
        path = messages.Entry(title, help, path, with_historic, with_complete,
                              basepath, curpath).run()
        if type(path) != type([]):
            return path
        else:
            app.show()
            path = path.pop()


def doDoubleEntry(title, help1, path1 = '', with_historic1 = 1, with_complete1 = 1,
                  help2 = '', path2 = '', with_historic2 = 1, with_complete2 = 1):
    active_entry = 0
    curpath1 = app.panels[app.panel].path
    curpath2 = app.panels[app.panel].path
    while 1:
        if with_complete1:
            if not path1 or path1 == '':
                basepath1 = app.panels[app.panel].path
            elif path1[0] == os.sep:
                basepath1 = path1[:]
            else:
                basepath1 = app.panels[app.panel].path
        else:
                basepath1 = ''
        if with_complete2:
            if not path2 or path2 == '':
                basepath2 = app.panels[app.panel].path
            elif path2[0] == os.sep:
                basepath2 = path2[:]
            else:
                basepath2 = app.panels[app.panel].path
        else:
            basepath2 = ''
        path = messages.DoubleEntry(title, help1, path1, with_historic1,
                                    with_complete1, basepath1, curpath1,
                                    help2, path2, with_historic2,
                                    with_complete2, basepath2, curpath2,
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
    app.run()

    
if __name__ == '__main__':
    import time, getopt

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

    DEBUGFILE = "./lfm-log.%d" % os.getuid()
    if DEBUG:
        debug = open(DEBUGFILE, 'w')
        debug.write('********** Start:   ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        sys.stdout = debug
        sys.stderr = debug

    curses.wrapper(main, paths, npanels)

    if DEBUG:
        debug.write('********** End:     ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        debug.close()

