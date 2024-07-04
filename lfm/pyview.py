#!/usr/bin/env python

# Copyright (C) 2001-2  Iñigo Serna
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
Copyright (C) 2001-2, Iñigo Serna <inigoserna@terra.es>.
All rights reserved.

This software has been realised under the GPL License, see the COPYING
file that comes with this package. There is NO WARRANTY.

'pyview' is a simple pager (viewer) to be used with Last File Manager.
"""


import os, os.path, sys
import curses, curses.ascii

from __init__ import *
import messages


##################################################
##### Internal View
##################################################
class InternalView:
    """Internal View class"""

    def __init__(self, title, buf, center = 1):
        self.title = title
        self.__validate_buf(buf, center)
        self.init_curses()


    def __validate_buf(self, buf, center):
        buf = [(l[0][:curses.COLS-2], l[1] ) for l in buf]
        buf2 = [l[0] for l in buf]
        self.nlines = len(buf2)
        if self.nlines > curses.LINES - 2:
            self.y0 = 0
            self.large = 1
            self.y = 0
        else:
            self.y0 = ((curses.LINES-2) - self.nlines)/2
            self.large = 0
        if center:
            col_max = max(map(len, buf2))
            self.x0 = (curses.COLS - col_max)/2
        else:
            self.x0 = 1
            if self.large:
                self.y0 = 0
            else:
                self.y0 = 1
        self.buf = buf


    def init_curses(self):
        curses.cbreak()
        curses.raw()
        curses.curs_set(0)
        try:
            self.win_title = curses.newwin(1, 0, 0, 0)
            self.win_body = curses.newwin(curses.LINES-2, 0, 1, 0)     # h, w, y, x
            self.win_status = curses.newwin(1, 0, curses.LINES-1, 0)
        except curses.error:
            print 'Can\'t create windows'
            sys.exit(-1)

        if curses.has_colors():
            self.win_title.attrset(curses.color_pair(1) | curses.A_BOLD)
            self.win_title.bkgdset(curses.color_pair(1))
            self.win_body.attrset(curses.color_pair(2))
            self.win_body.bkgdset(curses.color_pair(2))
            self.win_status.attrset(curses.color_pair(1))
            self.win_status.bkgdset(curses.color_pair(1))
        self.win_body.keypad(1)

        self.win_title.erase()
        self.win_status.erase()
        self.win_title.addstr(0, (curses.COLS-len(self.title))/2, self.title)
        if self.large:
            status = ''
        else:
            status = 'Press a key to continue'
            self.win_status.addstr(0, (curses.COLS-len(status))/2, status)

        self.win_title.refresh()
        self.win_status.refresh()


    def show(self):
        """show title, file and status bar"""

        self.win_body.erase()
        i = 0
        if self.large:
            for l, c in self.buf[self.y:self.y + curses.LINES - 2]:
                self.win_body.addstr(self.y0 + i, self.x0, l, curses.color_pair(c))
                i += 1
        else:
            for l, c in self.buf:
                self.win_body.addstr(self.y0 + i, self.x0, l, curses.color_pair(c))
                i += 1
        self.win_body.refresh()


    def run(self):
        self.show()

        if self.large:
            quit = 0
            while not quit:
                self.show()
                ch = self.win_body.getch()
                if ch in [ord('p'), ord('P'), curses.KEY_UP]:
                    if self.y != 0:
                        self.y -= 1
                if ch in [ord('n'), ord('N'), curses.KEY_DOWN]:
                    if self.y < self.nlines - 1:
                        self.y += 1
                elif ch in [curses.KEY_HOME, 348, 72]:
                    self.y = 0
                elif ch in [curses.KEY_END, 351, 70]:
                    self.y = self.nlines - 1
                elif ch in [curses.KEY_PPAGE, 0x08, 0x10, curses.KEY_BACKSPACE]:
                    self.y -= curses.LINES - 2
                    if self.y < 0:
                        self.y = 0
                elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:
                    self.y += curses.LINES - 2
                    if self.y > self.nlines - 1:
                        self.y = self.nlines - 1
                elif ch in [ord('q'), ord('Q'), ord('x'), ord('X'),
                            curses.KEY_F3, curses.KEY_F10]:
                    quit = 1
        else:
            while not self.win_body.getch():
                pass


##################################################
##### pyview
##################################################
class FileView:
    """Main application class"""

    def __init__(self, file, line, mode):
        self.file = file
        self.mode = mode
        self.wrap = 0
        self.init_curses()
        self.pos = 0
        self.col = 0
        try:
            self.__get_file_info(file)
        except OSError:
            sys.exit(-1)
        if self.nbytes == 0:
            messages.error('View \'%s\'' % file, 'File is empty')
            sys.exit(-1)
        if line > self.nlines:
            self.line = self.nlines
        self.fd = open(file)
        self.line = 0
        try:
            if mode == MODE_TEXT:
                self.__move_lines((line or 1) - 1)
            else:
                self.pos = line
                if self.pos > self.nbytes:
                    self.pos = self.nbytes
                self.__move_hex(0)
        except IndexError:
            pass
        self.pattern = ''
        self.matches = []
        i, a = os.popen4('which grep')
        r = a.read()
        i.close(); a.close()
        if r:
            self.grep = r.strip()
        else:
            self.grep = ''


    def __get_file_info(self, file):
        """get size and number of lines of the file"""
        
        self.nbytes = os.path.getsize(file)
        nlines = 0L
        self.lines_pos = [0L]
        if self.nbytes != 0:
            pos = 0L
            f = open(file)
            for l in f.readlines():
                pos += len(l)
                self.lines_pos.append(pos)
                nlines += 1
            f.close()
        self.nlines = nlines + 1


    def init_curses(self):
        """initialize curses stuff: windows, colors, ..."""

        curses.cbreak()
        curses.raw()
        curses.curs_set(0)
        try:
            self.win_title = curses.newwin(1, 0, 0, 0)
            self.win_file = curses.newwin(curses.LINES-2, 0, 1, 0)     # h, w, y, x
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
            self.win_file.attrset(curses.color_pair(2))
            self.win_file.bkgdset(curses.color_pair(2))
            self.win_status.attrset(curses.color_pair(1))
            self.win_status.bkgdset(curses.color_pair(1))
        self.win_file.keypad(1)


    def __move_lines(self, lines):
        if lines > 0:
            if self.line + lines > self.nlines - 1:
                self.line = self.nlines - 1
            else:
                self.line += lines
        else:
            if self.line + lines < 0:
                self.line = 0
            else:
                self.line += lines
        self.pos = self.lines_pos[self.line]
        self.fd.seek(self.lines_pos[self.line], 0)

    
    def __get_lines_text(self):
        lines = []
        for i in range(curses.LINES - 2):
            lines.append(self.fd.readline()[:-1].replace('\t', ' ' * 4))
        self.fd.seek(self.pos)
        self.col_max = max(map(len, lines))
        return lines


    def __get_prev_lines_text(self):
        lines = []
        i = 0
        for i in range(curses.LINES - 2):
            line_i = self.line - 1 - i
            if line_i < 0:
                break
            self.fd.seek(self.lines_pos[line_i])
            lines.append(self.fd.readline()[:-1].replace('\t', ' ' * 4))
        self.fd.seek(self.pos)
        return lines


    def __get_line_length(self):
        line = self.fd.readline()[:-1].replace('\t', ' ' * 4)
        self.fd.seek(self.pos)
        return len(line)


    def __get_1line(self):
        line = self.fd.readline()[:-1].replace('\t', ' ' * 4)
        self.fd.seek(self.pos)
        return line


    def show_chr(self, w, c):
        if curses.ascii.iscntrl(c) or ord(c) in range(0x7F, 0xA0):
            w.addch(ord('.'))
        elif curses.ascii.isascii(c):
            w.addch(curses.ascii.ascii(c))
        elif curses.ascii.ismeta(c):
                w.addstr(c)
        else:
            w.addch(ord('.'))


    def show_str(self, w, line):
        for i in range(len(line)):
            c = line[i]
            if ord(c) == ord('\r'):
                pass
            elif curses.ascii.iscntrl(c) or ord(c) in range(0x7F, 0xA0):
                w.addch(0, i, ord('.'))
            elif curses.ascii.isascii(c):
                w.addch(0, i, curses.ascii.ascii(c))
            elif curses.ascii.ismeta(c):
                w.addstr(0, i, c)
            else:
                w.addch(0, i, ord('.'))          


    def show_text_nowrap(self):
        lines = self.__get_lines_text()
        self.win_file.refresh()
        y = 0
        for l in lines:
            lwin = curses.newpad(1, curses.COLS + 1)
            lwin.erase()
            l = l[self.col:self.col + curses.COLS]
            if len(l) == curses.COLS:
                l = l[:curses.COLS-1]
                self.show_str(lwin, l)
                lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS-1)
                lwin2 = curses.newpad(1, 2)
                lwin2.erase()
                attr = curses.color_pair(2) | curses.A_BOLD
                lwin2.addch('>', attr)
                lwin2.refresh(0, 0, y + 1, curses.COLS-1, y + 1, curses.COLS-1)
                del(lwin2)
            else:
                self.show_str(lwin, l)
                lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS)
            del(lwin)
            y += 1
        self.win_file.refresh()

        
    def show_text_wrap(self):
        lines = self.__get_lines_text()
        lines[0] = lines[0][self.col:]   # show remaining chars of 1st line
        self.win_file.refresh()
        y = 0
        for l in lines:
            if y > curses.LINES - 2:
                break
            if len(l) <= curses.COLS:
                lwin = curses.newpad(1, curses.COLS + 1)
                lwin.erase()
                if len(l) != curses.COLS:
                    self.show_str(lwin, l)
                    lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS)
                else:
                    self.show_str(lwin, l[:-1])
                    lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS-1)
                    lwin2 = curses.newpad(1, 2)
                    lwin2.erase()
                    self.show_chr(lwin2, l[-1])
                    lwin2.refresh(0, 0, y + 1, curses.COLS-1,
                                  y + 1, curses.COLS-1)
                    del(lwin2)

                del(lwin)
                y += 1
            else:
                while len(l) > 0:
                    lwin = curses.newpad(1, curses.COLS + 1)
                    lwin.erase()
                    l2 = l[:curses.COLS]
                    if len(l2) == curses.COLS:
                        self.show_str(lwin, l2[:-1])
                        lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS-1)
                        lwin2 = curses.newpad(1, 2)
                        lwin2.erase()
                        self.show_chr(lwin2, l2[-1:])
                        lwin2.refresh(0, 0, y + 1, curses.COLS-1,
                                      y + 1, curses.COLS-1)
                        del(lwin2)
                    else:
                        self.show_str(lwin, l2)
                        lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS)
                    del(lwin)
                    y += 1
                    if y > curses.LINES - 2:
                        break
                    l = l[curses.COLS:]
        self.win_file.refresh()


    def __move_hex(self, lines):
        self.pos = self.pos & 0xFFFFFFF0
        if lines > 0:
            if self.pos + lines * 16 > self.nbytes - 1:
                self.pos = self.nbytes - 1
            else:
                self.pos += lines * 16
        else:
            if self.pos + lines * 16 < 0:
                self.pos = 0
            else:
                self.pos += lines * 16
        self.fd.seek(self.pos, 0)
        for i in range(len(self.lines_pos)):
            ls = self.lines_pos[i]
            if self.pos <= ls:
                if i > 0:
                    self.line = i - 1
                else:
                    self.line = 0
                break
        else:
            self.line = i


    def __get_lines_hex(self):
        self.__move_hex(0)
        lines = self.fd.read(16 * (curses.LINES - 2))
        le = len(lines)
        if le != 16 * (curses.LINES - 2):
            for i in range(16 * (curses.LINES - 2) - le):
                lines += chr(0)
        self.fd.seek(self.pos)
        return lines


    def show_hex(self):
        lines = self.__get_lines_hex()
        self.win_file.erase()
        self.win_file.refresh()
        for y in range(curses.LINES - 2):
            lwin = curses.newpad(1, curses.COLS + 1)
            lwin.erase()
            attr = curses.color_pair(2) | curses.A_BOLD
            lwin.addstr(0, 0, '%8.8X ' % (self.pos + 16 * y), attr)
            for i in range(4):
                buf = ''
                for j in range(4):
                    buf += '%2.2X ' % (ord(lines[y*16 + 4 * i + j]) & 0xFF)
                lwin.addstr(buf)
                if i != 3:
                    lwin.addch(curses.ACS_VLINE)
                    lwin.addch(' ')
            for i in range(16):
                c = lines[y*16 + i]
                if curses.ascii.iscntrl(c) or ord(c) in range(0x7F, 0xA0):
                    lwin.addch(ord('.'))
                elif curses.ascii.isascii(c):
                    lwin.addch(curses.ascii.ascii(c))
                elif curses.ascii.ismeta(c):
                     lwin.addstr(c)
                else:
                    lwin.addch(ord('.'))

            lwin.refresh(0, 0, y + 1, 0, y + 1, curses.COLS - 1)
        self.win_file.refresh()


    def show(self):
        """show title, file and status bar"""

        self.win_title.erase()
        self.win_file.erase()
        self.win_status.erase()

        # title
        title = os.path.basename(self.file)
        if len(title) > curses.COLS-51:
            title = title[:curses.COLS-57] + '~' + title[-5:]
        self.win_title.addstr('File: %s' % title)
        if self.col != 0 or self.wrap:
            self.win_title.addstr(0, curses.COLS / 2 - 14, 'Col: %d' % self.col)
        buf = 'Bytes: %d/%d' % (self.pos, self.nbytes)
        self.win_title.addstr(0, curses.COLS / 2 - 4, buf)
        buf = 'Lines: %d/%d' % (self.line + 1, self.nlines)
        self.win_title.addstr(0, curses.COLS * 3 / 4 - 4, buf)
        self.win_title.addstr(0, curses.COLS - 5,
                              '%3d%%' % (self.pos * 100 / self.nbytes))

        # file
        if self.mode == MODE_TEXT:
            if self.wrap:
                self.show_text_wrap()
            else:
                self.show_text_nowrap()
        else:
            self.show_hex()

        # status
        path = os.path.dirname(self.file)
        if not path or path[0] != os.sep:
            path = os.path.join(os.getcwd(), path)
        if len(path) > curses.COLS - 37:
            path = '~' + path[-(curses.COLS - 38):]
        self.win_status.addstr('Path: %s' % path)
        if self.mode == 0:
            mode = 'TEXT'
        else:
            mode = 'HEX'
        if self.wrap:
            wrap = 'YES'
        else:
            wrap = 'NO'
        self.win_status.addstr(0, curses.COLS - 30, 'View mode: %s' % mode)
        if self.mode == MODE_TEXT:
            self.win_status.addstr(0, curses.COLS - 10, 'Wrap: %s' % wrap)

        self.win_title.refresh()
        self.win_file.refresh()
        self.win_status.refresh()


    def __find(self, title):
        if not self.grep:
            self.show()
            messages.error('Find Error', 'Can\'t find grep')
            return -1
        self.pattern = messages.Entry(title, 'Type search string', '', 1, 0).run()
        if self.pattern == None or self.pattern == '':
            self.show()
            return -1
        filename = os.path.abspath(self.file)
        mode = (self.mode == MODE_TEXT) and 'n' or 'b'
        try:
            buf = os.popen('%s -i%c \"%s\" \"%s\"' % \
                           (self.grep, mode, self.pattern, filename)).readlines()
        except:
            self.show()
            messages.error('Find Error', 'Can\'t popen file')
            return -1
        try:
            self.matches = [int(l[:l.find(':')]) for l in buf]
        except ValueError:
            self.matches = []


    def __find_next(self):
        pos = (self.mode == MODE_TEXT) and self.line or self.pos + 16
        for next in self.matches:
            if next <= pos + 1:
                continue
            else:
                break
        else:
            self.show()
            messages.error('Find',
                           'No more matches <%s>' % self.pattern)
            self.show()
            return
        if self.mode == MODE_TEXT:
            self.line = next - 1
            self.__move_lines(0)
        else:
            self.pos = next
            self.__move_hex(0)
        self.show()


    def __find_previous(self):
        pos = (self.mode == MODE_TEXT) and self.line or self.pos
        rev_matches = [l for l in self.matches]
        rev_matches.reverse()
        for prev in rev_matches:
            if prev >= pos + 1:
                continue
            else:
                break
        else:
            self.show()
            messages.error('Find',
                           'No more matches <%s>' % self.pattern)
            self.show()
            return
        if self.mode == MODE_TEXT:
            self.line = prev - 1
            self.__move_lines(0)
        else:
            self.pos = prev
            self.__move_hex(0)
        self.show()


    def run(self):
        """run application, manage keys, etc"""

        self.show()
        while 1:
            chext = 0
            ch = self.win_file.getch()

            # to avoid extra chars input
            if ch == 0x1B:
                chext = 1
                ch = self.win_file.getch()
                ch = self.win_file.getch()

            # cursor up
            if ch in [ord('p'), ord('P'), curses.KEY_UP]:
                if self.mode == MODE_TEXT:
                    if self.wrap:
                        if self.col == 0:
                            if self.line > 0:
                                self.__move_lines(-1)
                                self.col = self.__get_line_length() / curses.COLS * curses.COLS
                        else:
                            self.col -= curses.COLS
                    else:
                        self.__move_lines(-1)
                else:
                    self.__move_hex(-1)
                self.show()
            # cursor down
            elif ch in [ord('n'), ord('N'), curses.KEY_DOWN]:
                if self.mode == MODE_TEXT:
                    if self.wrap:
                        self.col += curses.COLS
                        if self.col >= self.__get_line_length():
                            self.col = 0
                            self.__move_lines(1)
                    else:
                        self.__move_lines(1)
                else:
                    self.__move_hex(1)
                self.show()
            # page previous
            elif ch in [curses.KEY_PPAGE, curses.KEY_BACKSPACE,
                        0x08, 0x10]:                         # BackSpace, Ctrl-P
                if self.mode == MODE_TEXT:
                    if self.wrap:
                        lines = self.__get_prev_lines_text()
                        if self.col:     # if we aren't at 1st char of line
                            line0 = self.__get_1line()[:self.col]
                            lines.insert(0, line0)
                        else:
                            line0 = ''
                        y = curses.LINES - 2
                        for i in range(len(lines)):
                            y -= 1
                            dy = 0
                            if y < 0:
                                break
                            exit1 = 0
                            len2 = len(lines[i])
                            lenz = len2
                            while len2 > curses.COLS:
                                dy += 1
                                y -= 1
                                if y < 0:
                                    i += 1
                                    dy = lenz / curses.COLS + 1 - dy
                                    exit1 = 1
                                    break
                                len2 -= curses.COLS
                            if exit1:
                                break
                        else:
                            i += 1
                        if line0:
                            i -= 1
                        if y < 0:
                            self.__move_lines(-i)
                            if i == 0:
                                self.col = (dy - 1) * curses.COLS
                            else:
                                self.col = dy * curses.COLS
                        else:
                            self.__move_lines(-(curses.LINES-2))
                            self.col = 0
                    else:
                        self.__move_lines(-(curses.LINES-2))
                else:
                    self.__move_hex(-(curses.LINES-2))
                self.show()
            # page next
            elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:   # Ctrl-N
                if self.mode == MODE_TEXT:
                    if self.wrap:
                        lines = self.__get_lines_text()
                        lines[0] = lines[0][self.col:]
                        y = 0
                        for i in range(len(lines)):
                            y += 1
                            dy = 0
                            if y > curses.LINES - 2:
                                break
                            exit1 = 0
                            len2 = len(lines[i])
                            while len2 > curses.COLS:
                                dy += 1
                                y += 1
                                if y > curses.LINES - 2:
                                    exit1 = 1
                                    break
                                len2 -= curses.COLS
                            if exit1:
                                break
                        else:
                            i += 1
                        self.__move_lines(i)
                        if i == 0:
                            self.col += dy * curses.COLS
                        else:
                            self.col = dy * curses.COLS
                    else:
                        self.__move_lines(curses.LINES-2)
                else:
                    self.__move_hex(curses.LINES-2)
                self.show()
            # home
            elif (ch in [curses.KEY_HOME, 348]) or \
                 (chext == 1) and (ch == 72):  # home
                if self.mode == MODE_TEXT:
                    self.__move_lines(-self.nlines)
                else:
                    self.__move_hex(-self.nbytes)                    
                self.col = 0
                self.show()
            # end
            elif (ch in [curses.KEY_END, 351]) or \
                 (chext == 1) and (ch == 70):   # end
                if self.mode == MODE_TEXT:
                    self.__move_lines(self.nlines)
                else:
                    self.__move_hex(self.nbytes)
                self.col = 0
                self.show()
            
            # cursor left
            elif ch in [curses.KEY_LEFT]:
                if self.mode == MODE_HEX or self.wrap:
                    continue
                if self.col > 9:
                    self.col -= 10
                    self.show()
            # cursor right
            elif ch in [curses.KEY_RIGHT]:
                if self.mode == MODE_HEX or self.wrap:
                    continue
                if self.col + curses.COLS < self.col_max + 2:
                    self.col += 10
                    self.show()

            # un/wrap
            elif ch in [ord('w'), ord('W'), curses.KEY_F2]:
                if self.mode == MODE_HEX:
                    continue
                if self.wrap:
                    self.wrap = 0
                else:
                    self.wrap = 1
                self.col = 0
                self.show()

            # text / hexadecimal mode
            elif ch in [ord('m'), ord('M'), curses.KEY_F4]:
                if self.mode == MODE_TEXT:
                    self.mode = MODE_HEX
                    self.col = 0
                else:
                    self.mode = MODE_TEXT
                    self.__move_lines(0)
                self.show()

            #  goto line/byte
            elif ch in [ord('g'), ord('G'), curses.KEY_F5]:
                rel = 0
                if self.mode == MODE_TEXT:
                    title = 'Goto line'
                    help = 'Type line number'
                else:
                    title = 'Goto byte'
                    help = 'Type byte number'
                n = messages.Entry(title, help, '', 1, 0).run()
                if n == None or n == '':
                    self.show()
                    continue
                if n[0] == '+' or n[0] == '-':
                    rel = 1
                try:
                    if n[rel:rel+2] == '0x':
                        if rel:
                            n = long(n[0] + str(int(n[1:], 16)))
                        else:
                            n = long(n, 16)
                    else:
                        n = long(n)
                except ValueError:
                    self.show()
                    if self.mode == MODE_TEXT:
                        messages.error('Goto line',
                                       'Invalid line number <%s>' % n)
                    else:
                        messages.error('Goto byte',
                                       'Invalid byte number <%s>' % n)
                    self.show()
                    continue

                if self.mode == MODE_TEXT:
                    if rel:
                        self.line += n
                    else:
                        self.line = n - 1
                    if self.line > self.nlines:
                        self.line = self.nlines - 1
                    self.__move_lines(0)
                else:
                    if rel:
                        self.pos += n
                    else:
                        self.pos = n
                    if self.pos > self.nbytes:
                        self.pos = self.nbytes
                    self.__move_hex(0)
                self.show()

            #  find
            elif ch in [ord('/')]:
                if self.__find('Find') == -1:
                    continue
                self.__find_next()
                
            # find previous
            elif ch in [curses.KEY_F6]:
                if not self.matches:
                    if self.__find('Find Previous') == -1:
                        continue
                self.__find_previous()

            # find next
            elif ch in [curses.KEY_F7]:
                if not self.matches:
                    if self.__find('Find Next') == -1:
                        continue
                self.__find_next()

            #  help
            elif ch in [ord('h'), ord('H'), curses.KEY_F1]:
                buf = [('', 2)]
                buf.append(('%s v%s (C) %s, by %s' % \
                            (PYVIEW_NAME, VERSION, DATE, AUTHOR), 5))
                text = PYVIEW_README.split('\n')
                for l in text:
                    buf.append((l, 6))
                InternalView('Help for %s' % PYVIEW_NAME, buf).run()
                self.show()

            # quit
            elif ch in [ord('q'), ord('Q'), ord('x'), ord('X'),
                        curses.KEY_F3, curses.KEY_F10]:
                self.fd.close()
                return


##################################################
##### Main
##################################################
def usage(prog, msg = ""):
    prog = os.path.basename(prog)
    if msg != "":
        print '%s:\t%s\n' % (prog, msg)
    print """\
%s v%s - (C) %s, by %s

A simple pager (viewer) to be used with Last File Manager.
Released under GNU Public License, read COPYING for more details.

Usage:\t%s\t[-h | --help]
\t\t[-d | --debug]
\t\t[-m text|hex | --mode=text|hex]
\t\t[+n]
\t\tpathtofile
Options:
    -m, --mode\t\tstart in text or hexadecimal mode
    -d, --debug\t\tcreate debug file
    -h, --help\t\tshow help
    +n\t\t\tstart at line (text mode) or byte (hex mode),
    \t\t\tif n starts with '0x' is considered hexadecimal
    pathtofile\t\tfile to view
""" % (PYVIEW_NAME, VERSION, DATE, AUTHOR, prog)


def main(win, file, line, mode):

    app = FileView(file, line, mode)
    if app == OSError:
        sys.exit(-1)
    return app.run()


def PyView(sysargs):
    import time, getopt

    # defaults
    DEBUG = 0
    line = 0
    mode = MODE_TEXT
    
    # args
    try:
        opts, args = getopt.getopt(sysargs[1:], 'dhm:',
                                   ['debug', 'help', 'mode='])
    except getopt.GetoptError:
        usage(sysargs[0], 'Bad argument(s)')
        sys.exit(-1)
    for o, a in opts:
        if o in ('-d', '--debug'):
            DEBUG = 1
        elif o in ('-h', '--help'):
            usage(sysargs[0])
            sys.exit(2)
        elif o in ('-m', '--mode'):
            if a == 'text':
                mode = MODE_TEXT
            elif a == 'hex':
                mode = MODE_HEX
            else:
                usage(sysargs[0], '<%s> is not a valid mode' % a)
                sys.exit(-1)

    if len(args) == 0:
        usage(sysargs[0], 'File is missing')
        sys.exit(-1)
    elif len(args) == 1:
        if args[0][0] == '+':
            usage(sysargs[0], 'File is missing')
            sys.exit(-1)
        elif not os.path.isfile(args[0]):
            usage(sysargs[0], '<%s> is not a valid file' % args[0])
            sys.exit(-1)
        file = args[0]
    elif len(args) == 2:
        if args[0][0] == '+':
            line = args[0][1:]
            file = args[1]
        elif args[1][0] == '+':
            line = args[1][1:]
            file = args[0]
        else:
            print 'HERE'
            usage(sysargs[0], 'Bad argument(s)')
            sys.exit(-1)
        try:
            if line[:2] == '0x':
                line = int(line, 16)
            else:
                line = int(line)
        except ValueError:
            usage(sysargs[0], '<%s> is not a valid line number' % line)
            sys.exit(-1)
        if not os.path.isfile(file):
            usage(syssarg[0], '<%s> is not a valid file' % file)            
            sys.exit(-1)
    else:
        usage(sysargs[0], 'Incorrect number of arguments')
        sys.exit(-1)

    DEBUGFILE = "./pyview-log.%d" % os.getpid()
    if DEBUG:
        debug = open(DEBUGFILE, 'w')
        debug.write('********** Start:   ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        sys.stdout = debug
        sys.stderr = debug

    curses.wrapper(main, file, line, mode)
    
    if DEBUG:
        debug.write('********** End:     ')
        debug.write(time.ctime(time.time()) + ' **********\n')
        debug.close()

    sys.stdout = sys.__stdout__
    sys.stdout = sys.__stderr__


if __name__ == '__main__':
    PyView(sys.argv)
