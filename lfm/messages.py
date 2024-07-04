# -*- coding: utf-8 -*-

"""messages.py

This module contains some windows for lfm use.
"""


import sys
import os.path
import curses
import curses.panel
import files


######################################################################
##### module variables
app = None
historic = []
HISTORIC_MAXLEN = 100


######################################################################
class CommonWindow:
    """A superclass for 'error' and 'win' windows"""

    def __init__(self, title, text, br_att, br_bg, bd_att, bd_bg, waitkey = 1):
        self.waitkey = waitkey
        text = text.replace('\t', ' ' * 4)
        lines = text.split('\n')
        length = max(map(len, lines))
        if self.waitkey:
            w = min(max(max(length+6, 27+4), len(title)+6), app.maxw-2)
            if length < 27 + 4 and len(title) <= length:
                w -= 1
        else:
            w = min(max(length+6, len(title)+6), app.maxw-2)
            if len(title) < length:
                w -= 1
        h = len(lines) + 4
        for l in lines:
            h += int((len(l)+1) / (app.maxw-2))
        if h > app.maxh - 4:
            h = app.maxh - 4
            text = ''.join([l+'\n' for l in lines[-5:]])
        try:
            win = curses.newwin(h, w,
                                int((app.maxh-h)/2), int((app.maxw-w)/2))
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.bkgd(br_bg, br_att)
        win.erase()
        win.box(0, 0)
        if len(title) > app.maxw-14:
            title = title[:app.maxw-10] + '...' + '\''
        win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title, curses.A_BOLD)
        if h == 5:
            win.addstr(2, 2, text, bd_att)
        else:
            win.addstr(2, 1, text, bd_att)
        if self.waitkey:
            win.addstr(h-1, int((w-27)/2), ' Press any key to continue ', br_att)
        win.refresh()
        win.keypad(1)

    def run(self):
        if self.waitkey:
            while not self.pwin.window().getch():
                pass
        self.pwin.hide()


class FixSizeCommonWindow:
    """A superclass for messages, with fixed size"""

    def __init__(self, title, text, downtext,
                 br_att, br_bg, bd_att, bd_bg, waitkey = 1):
        self.waitkey = waitkey
        text = text.replace('\t', ' ' * 4)
        w = app.maxw - 20
        if len(title) > w - 4:
            title = title[:w-4]
        if len(text) > w - 4:
            text = text[:w-5]
        if len(downtext) > w - 4:
            downtext = downtext[:w-4]
        h = 5
        try:
            win = curses.newwin(h, w,
                                int((app.maxh-h)/2), int((app.maxw-w)/2))
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.bkgd(br_bg, br_att)
        win.erase()
        win.box(0, 0)
        if len(title) > app.maxw - 14:
            title = title[:app.maxw-10] + '...' + '\''
        win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title, curses.A_BOLD)
        if h == 5:
            win.addstr(2, 2, text, bd_att)
        else:
            win.addstr(2, 1, text, bd_att)
        if self.waitkey:
            win.addstr(h-1, int((w-27)/2),
                       ' Press any key to continue ', br_att)
        elif downtext:
            win.addstr(h-1, int((w-len(downtext)-2)/2),
                       ' %s ' % downtext, br_att)
        win.refresh()
        win.keypad(1)

    def run(self):
        if self.waitkey:
            while not self.pwin.window().getch():
                pass
        self.pwin.hide()


class FixSizeProgressBarWindow:
    """Like FixSizeCommonWindow but with a ProgressBar"""

    def __init__(self, title, text, downtext, percent,
                 bd_att, bd_bg, pb_att, pb_bg, waitkey = 1):
        title = title[:app.maxw-14]
        text = text[:app.maxw-14]
        self.waitkey = waitkey
        text = text.replace('\t', ' ' * 4)
        w = app.maxw - 20
        if len(title) > w - 4:
            title = title[:w-4]
        if len(text) > w - 4:
            text = text[:w-5]
        if len(downtext) > w - 4:
            downtext = downtext[:w-4]
        h = 7
        self.h, self.w = h, w
        self.bd_att, self.pb_att = bd_att, pb_att
        try:
            win = curses.newwin(h, w,
                                int((app.maxh-h)/2), int((app.maxw-w)/2))
            self.progressbar = curses.newpad(1, w-11+1)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.bkgd(bd_bg, bd_att)
        self.progressbar.bkgd(curses.ACS_CKBOARD, pb_bg)
        win.erase()
        win.keypad(1)

    def show(self, title, text, downtext, percent):
        self.pwin.window().erase()
        self.pwin.window().box(0, 0)
        if len(title) > app.maxw - 14:
            title = title[:app.maxw-10] + '...' + '\''
        self.pwin.window().addstr(0, int((self.w-len(title)-2)/2),
                                  ' %s ' % title, curses.A_BOLD)
        self.pwin.window().addstr(2, 2, text)
        w1 = percent * (self.w-11) / 100
        self.progressbar.erase()
        self.progressbar.addstr(0, 0, ' ' * w1, self.pb_att | curses.A_BOLD)
        self.pwin.window().addstr(self.h-3, self.w-8, '[%3d%%]' % percent)
        if self.waitkey:
            self.pwin.window().addstr(self.h-1, int((self.w-27)/2),
                                      ' Press any key to continue ')
        elif downtext:
            self.pwin.window().addstr(self.h-1, int((self.w-len(downtext)-2)/2),
                                      ' %s ' % downtext)
        self.pwin.window().refresh()
        y0 = int((app.maxh-self.h)/2) + 4
        x0 = int((app.maxw-self.w)/2) + 2
        self.progressbar.refresh(0, 0, y0, x0, y0+1, x0+self.w-12)
        self.pwin.window().refresh()


######################################################################
def error(title, msg = '', file = ''):
    """show an error window"""

    if file == '':
        buf = msg
    else:
        buf = '%s: %s' % (file, msg)
    CommonWindow(title, buf,
                 curses.color_pair(8),
                 curses.color_pair(8),
                 curses.color_pair(7) | curses.A_BOLD,
                 curses.color_pair(7)).run()


######################################################################
def win(title, text):
    """show a message window and wait for a key"""

    CommonWindow(title, text,
                 curses.color_pair(1), curses.color_pair(1),
                 curses.color_pair(4), curses.color_pair(4)).run()


def win_nokey(title, text, downtext = ''):
    """show a message window, does not wait for a key"""

    FixSizeCommonWindow(title, text, downtext,
                        curses.color_pair(1), curses.color_pair(1),
                        curses.color_pair(1), curses.color_pair(1),
                        waitkey = 0).run()


######################################################################
def notyet(title):
    """show a not-yet-implemented message"""

    CommonWindow(title,
                 'Sorry, but this function\n is not implemented yet!',
                 curses.color_pair(1) | curses.A_BOLD, curses.color_pair(1),
                 curses.color_pair(4), curses.color_pair(4)).run()


######################################################################
def get_a_key(title, question):
    """show a window returning key pressed"""

    question = question.replace('\t', ' ' * 4)
    lines = question.split('\n')
    length = max(map(len, lines))
    h = min(len(lines)+4, app.maxh-2)
    w = min(length+4, app.maxw-2)
    try:
        win = curses.newwin(h, w, int((app.maxh-h)/2), int((app.maxw-w)/2))
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    win.bkgd(curses.color_pair(1))

    win.erase()
    win.box(0, 0)
    win.addstr(0, int((w-len(title)-2)/2), ' %s' % title,
               curses.color_pair(1) | curses.A_BOLD)
    for row, l in enumerate(lines):
        win.addstr(row+2, 2, l)
    win.refresh()
    win.keypad(1)
    while True:
        ch = win.getch()
        if ch in (0x03, 0x1B):       # Ctrl-C, ESC
            pwin.hide()
            return -1
        elif 0x01 <= ch <= 0xFF:
            pwin.hide()
            return ch
        else:
            curses.beep()


######################################################################
def confirm(title, question, default = 0):
    """show a yes/no window, returning 1/0"""

    h = 5
    w = min(max(34, len(question)+5), app.maxw-2)
    try:
        win = curses.newwin(h, w, int((app.maxh-h)/2), int((app.maxw-w)/2))
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    win.bkgd(curses.color_pair(1))

    win.erase()
    win.box(0, 0)
    win.addstr(0, int((w-len(title)-2)/2), ' %s' % title.capitalize(),
               curses.color_pair(1) | curses.A_BOLD)
    win.addstr(1, 2 , '%s?' % question)
    win.refresh()

    row = int((app.maxh-h)/2) + 3
    col = int((app.maxw-w)/2)
    col1 = col + int(w/5) + 1
    col2 = col + int(w*4/5) - 6
    win.keypad(1)
    answer = default
    while True:
        if answer == 1:
            attr_yes = curses.color_pair(9) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
        else:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(9) | curses.A_BOLD
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row + 1, col1 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col2, row + 1, col2 + 5)

        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT,
                  curses.KEY_RIGHT, 9):
            answer = not answer
        elif ch in (ord('Y'), ord('y')):
            answer = 1
            break
        elif ch in (ord('N'), ord('n')):
            answer = 0
            break
        elif ch in (0x03, 0x1B):    # Ctrl-C, ESC
            answer = -1
            break
        elif ch in (10, 13):        # enter
            break
        else:
            curses.beep()

    pwin.hide()
    return answer


######################################################################
def confirm_all(title, question, default = 0):
    """show a yes/all/no/stop window, returning 1/2/0/-1"""

    h = 5
    w = min(max(45, len(question)+5), app.maxw-2)
    try:
        win = curses.newwin(h, w, int((app.maxh-h)/2), int((app.maxw-w)/2))
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    win.bkgd(curses.color_pair(1))

    win.erase()
    win.box(0, 0)
    win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title,
               curses.color_pair(1) | curses.A_BOLD)
    win.addstr(1, 2 , '%s?' % question)
    win.refresh()

    row = int((app.maxh-h) / 2) + 3
    col = int((app.maxw-w) / 2)
    x = (w-28) / 5
    col1 = col + x + 1
    col2 = col1 + 7 + x
    col3 = col2 + 7 + x
    col4 = col3 + 6 + x

    win.keypad(1)
    answer = default
    while True:
        if answer == 1:
            attr_yes = curses.color_pair(9) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == 2:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(9) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == 0:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(9) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == -1:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(9) | curses.A_BOLD
        else:
            raise ValueError
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row + 1, col1 + 6)
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ All ]', attr_all)
        btn.refresh(0, 0, row, col2, row + 1, col2 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col3, row + 1, col3 + 5)
        btn = curses.newpad(1, 15)
        btn.addstr(0, 0, '[ Stop ]', attr_skipall)
        btn.refresh(0, 0, row, col4, row + 1, col4 + 7)

        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT,
                  curses.KEY_RIGHT, 9):
            if answer == 1:
                answer = 2
            elif answer == 2:
                answer = 0
            elif answer == 0:
                answer = -1
            elif answer == -1:
                answer = 1
            else:
                raise ValueError
        elif ch in (ord('Y'), ord('y')):
            answer = 1
            break
        elif ch in (ord('A'), ord('a')):
            answer = 2
            break
        elif ch in (ord('N'), ord('n')):
            answer = 0
            break
        elif ch in (ord('S'), ord('s'), 0x03, 0x1B):    # Ctrl-C, ESC
            answer = -1
            break
        elif ch in (10, 13):        # enter
            break
        else:
            curses.beep()

    pwin.hide()
    return answer


######################################################################
def confirm_all_none(title, question, default = 0):
    """show a yes/all/no/none/stop window, returning 1/2/0/-2/-1"""

    h = 5
    w = min(max(50, len(question)+5), app.maxw-2)
    try:
        win = curses.newwin(h, w, int((app.maxh-h)/2), int((app.maxw-w)/2))
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    win.bkgd(curses.color_pair(1))

    win.erase()
    win.box(0, 0)
    win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title,
               curses.color_pair(1) | curses.A_BOLD)
    win.addstr(1, 2 , '%s?' % question)
    win.refresh()

    row = int((app.maxh-h) / 2) + 3
    col = int((app.maxw-w) / 2)
    x = (w-36) / 6
    col1 = col + x + 1
    col2 = col1 + 7 + x
    col3 = col2 + 7 + x
    col4 = col3 + 6 + x
    col5 = col4 + 8 + x

    win.keypad(1)
    answer = default
    while True:
        if answer == 1:
            attr_yes = curses.color_pair(9) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_none = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == 2:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(9) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_none = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == 0:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(9) | curses.A_BOLD
            attr_none = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == -2:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_none = curses.color_pair(9) | curses.A_BOLD
            attr_skipall = curses.color_pair(1) | curses.A_BOLD
        elif answer == -1:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
            attr_none = curses.color_pair(1) | curses.A_BOLD
            attr_skipall = curses.color_pair(9) | curses.A_BOLD
        else:
            raise ValueError
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row + 1, col1 + 6)
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ All ]', attr_all)
        btn.refresh(0, 0, row, col2, row + 1, col2 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col3, row + 1, col3 + 5)
        btn = curses.newpad(1, 9)
        btn.addstr(0, 0, '[ NOne ]', attr_none)
        btn.refresh(0, 0, row, col4, row + 1, col4 + 7)
        btn = curses.newpad(1, 9)
        btn.addstr(0, 0, '[ Stop ]', attr_skipall)
        btn.refresh(0, 0, row, col5, row + 1, col5 + 7)

        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT,
                  curses.KEY_RIGHT, 9):
            if answer == 1:
                answer = 2
            elif answer == 2:
                answer = 0
            elif answer == 0:
                answer = -2
            elif answer == -2:
                answer = -1
            elif answer == -1:
                answer = 1
            else:
                raise ValueError
        elif ch in (ord('Y'), ord('y')):
            answer = 1
            break
        elif ch in (ord('A'), ord('a')):
            answer = 2
            break
        elif ch in (ord('N'), ord('n')):
            answer = 0
            break
        elif ch in (ord('O'), ord('o')):
            answer = -2
            break
        elif ch in (ord('S'), ord('s'), 0x03, 0x1B):    # Ctrl-C, ESC
            answer = -1
            break
        elif ch in (10, 13):        # enter
            break
        else:
            curses.beep()

    pwin.hide()
    return answer


######################################################################
class Yes_No_Buttons:
    """Yes/No buttons"""

    def __init__(self, w, h, d):
        self.row = int((app.maxh-h) / 2) + 4 + d
        col = int((app.maxw-w) / 2)
        self.col1 = col + int(w/5) + 1
        self.col2 = col + int(w*4/5) - 6
        self.active = 0


    def show(self):
        if self.active == 0:
            attr1 = curses.color_pair(1) | curses.A_BOLD
            attr2 = curses.color_pair(1) | curses.A_BOLD
        elif self.active == 1:
            attr1 = curses.color_pair(9) | curses.A_BOLD
            attr2 = curses.color_pair(1) | curses.A_BOLD
        else:
            attr1 = curses.color_pair(1) | curses.A_BOLD
            attr2 = curses.color_pair(9) | curses.A_BOLD
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[<Yes>]', attr1)
        btn.refresh(0, 0, self.row, self.col1, self.row + 1, self.col1 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr2)
        btn.refresh(0, 0, self.row, self.col2, self.row + 1, self.col2 + 5)


    def manage_keys(self):
        tmp = curses.newpad(1, 1)
        while True:
            ch = tmp.getch()
            if ch in (0x03, 0x1B):      # Ctrl-C, ESC
                return -1
            elif ch == ord('\t'):
                return ch
            elif ch in (10, 13):        # enter
                if self.active == 1:
                    return 10
                else:
                    return -1
            else:
                curses.beep()


######################################################################
class EntryLine:
    """An entry line to enter a dir. or file, a pattern, etc"""

    def __init__(self, w, h, x, y, path, with_historic, with_complete,
                 panelpath):
        try:
            self.entry = curses.newwin(1, w-4+1, x, y)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        self.entry.attrset(curses.color_pair(11) | curses.A_BOLD)
        self.entry.keypad(1)

        self.entry_width = w - 4
        self.text = path
        self.panelpath = panelpath
        self.pos = len(self.text)
        self.ins = True

        self.with_complete = with_complete
        self.with_historic = with_historic
        if self.with_historic:
            self.historic = historic[:]
            self.historic_i = len(self.historic)


    def show(self):
        text = self.text
        pos = self.pos
        ew = self.entry_width
        ltext = len(text)
        if pos < ew:
            relpos = pos
            if ltext < ew:
                textstr = text + ' ' * (ew - ltext)
            else:
                textstr = text[:ew]
        else:
            if pos > ltext - (ew-1):
                relpos = ew - 1 - (ltext - pos)
                textstr = text[ltext-ew+1:] + ' '
            else:
                relpos = pos - int(pos/ew)*ew
                textstr = text[int(pos/ew)*ew:int(pos/ew)*ew+ew]
        self.entry.bkgd(curses.color_pair(1))
        self.entry.erase()
        self.entry.addstr(textstr[:ew], curses.color_pair(11) | curses.A_BOLD)
        self.entry.move(0, relpos)
        self.entry.refresh()


    def manage_keys(self):
        while True:
            self.show()
            ch = self.entry.getch()
#              print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                    (curses.keyname(ch), ch & 255, ch, ch)
            if ch in (0x03, 0x1B):        # Ctrl-C, ESC
                return -1
            elif ch == curses.KEY_UP:
                if self.with_historic:
                    if self.historic_i > 0:
                        if self.historic_i == len(self.historic):
                            if self.text == None:
                                self.text = ''
                            self.historic.append(self.text)
                        self.historic_i -= 1
                        self.text = self.historic[self.historic_i]
                        self.pos = len(self.text)
                else:
                    continue
            elif ch == curses.KEY_DOWN:
                if self.with_historic:
                    if self.historic_i < len(self.historic) - 1:
                        self.historic_i += 1
                        self.text = self.historic[self.historic_i]
                        self.pos = len(self.text)
                else:
                    continue
            elif ch == ord('\t'):        # tab
                return ch
            elif ch in (10, 13):         # enter
                return 10
            elif ch == 0x14:             # Ctrl-T
                if self.with_complete:
                    entries = files.complete(self.text, self.panelpath)
                    if not entries:
                        curses.beep()
                        continue
                    elif len(entries) == 1:
                        selected = entries.pop()
                    else:
                        y, x = self.entry.getbegyx()
                        selected = SelectItem(entries, y + 1, x - 2).run()
                        app.display()
                        cursor_show2()
                    if selected != -1:
                        self.text = files.join(self.text, selected)
                        self.pos = len(self.text)
                    return 0x14
                else:
                    continue
            # chars and edit keys
            elif ch == 0x17:          # Ctrl-W
                if self.text == None or self.text == '':
                    continue
                text = self.text
                if text == os.sep:
                    text = ''
                else:
                    if text[len(text)-1] == os.sep:
                        text = os.path.dirname(text)
                    text = os.path.dirname(text)
                    if text != '' and text != os.sep:
                        text += os.sep
                self.text = text
                self.pos = len(self.text)
            elif ch == 0x04:          # Ctrl-D
                if self.text == None or self.text == '':
                    continue
                text = ''
                self.text = text
                self.pos = len(self.text)
            elif ch == curses.KEY_IC: # insert
                self.ins = not self.ins
            elif ch in (curses.KEY_HOME, 0x01):  # home
                self.pos = 0
            elif ch in (curses.KEY_END, 0x05):   # end
                self.pos = len(self.text)
            elif ch == curses.KEY_LEFT and self.pos > 0:
                self.pos -= 1
            elif ch == curses.KEY_RIGHT and self.pos < len(self.text):
                self.pos += 1
            elif ch in (8, 127, curses.KEY_BACKSPACE) and len(self.text) > 0 and \
                 self.pos > 0:    # backspace
                self.text = self.text[:self.pos-1] + self.text[self.pos:]
                self.pos -= 1
            elif ch == curses.KEY_DC and self.pos < len(self.text):  # del
                self.text = self.text[:self.pos] + self.text[self.pos+1:]
            elif len(self.text) < 255 and 32 <= ch <= 255:
                if self.ins:
                    self.text = self.text[:self.pos] + chr(ch) + self.text[self.pos:]
                    self.pos += 1
                else:
                    self.text = self.text[:self.pos] + chr(ch) + self.text[self.pos+1:]
                    self.pos += 1
            else:
                curses.beep()


######################################################################
class Entry:
    """An entry window to enter a dir. or file, a pattern, ..."""

    def __init__(self, title, help, path = '', with_historic = 1,
                 with_complete = 1, panelpath = ''):
        h = 6
        w = min(max(34, len(help)+5), app.maxw-2)
        try:
            win = curses.newwin(h, w, int((app.maxh-h)/2), int((app.maxw-w)/2))
            self.entry = EntryLine(w, h,
                                   int((app.maxh-h)/2)+2, int((app.maxw-w+4)/2),
                                   path, with_historic, with_complete,
                                   panelpath)
            self.btns = Yes_No_Buttons(w, h, 0)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.bkgd(curses.color_pair(1))
        win.erase()
        win.box(0, 0)
        win.addstr(1, 2 , '%s:' % help)
        win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title,
                   curses.color_pair(1) | curses.A_BOLD)
        win.refresh()

        self.with_historic = with_historic
        self.active_widget = self.entry


    def run(self):
        self.entry.entry.refresh() # needed to avoid a problem with blank paths
        self.entry.show()
        self.btns.show()
        cursor_show2()

        quit = False
        while not quit:
            self.btns.show()
            ans = self.active_widget.manage_keys()
            if ans == -1:              # Ctrl-C
                quit = True
                answer = None
            elif ans == ord('\t'):     # tab
                if self.active_widget == self.entry:
                    self.active_widget = self.btns
                    self.btns.active = 1
                    cursor_hide()
                    answer = self.entry.text
                elif self.active_widget == self.btns and self.btns.active == 1:
                    self.btns.active = 2
                    cursor_hide()
                    answer = None
                else:
                    self.active_widget = self.entry
                    self.btns.active = 0
                    cursor_show2()
            elif ans == 0x14:            # Ctrl-T
                # this is a hack, we need to return to refresh Entry
                return [self.entry.text]
            elif ans == 10:              # return values
                quit = True
                answer = self.entry.text

        cursor_hide()
        if answer:
            # save new historic entries
            if self.with_historic:
                if self.entry.text and self.entry.text != '*':
                    if len(historic) < HISTORIC_MAXLEN:
                        historic.append(self.entry.text)
                    else:
                        historic.reverse()
                        historic.pop()
                        historic.reverse()
                        historic.append(self.entry.text)
        self.pwin.hide()
        return answer


######################################################################
class DoubleEntry:
    """An entry window to enter 2 dirs. or files, patterns, ..."""

    def __init__(self, title, help1 = '', path1 = '',
                 with_historic1 = 1, with_complete1 = 1, panelpath1 = '',
                 help2 = '', path2 = '',
                 with_historic2 = 1, with_complete2 = 1, panelpath2 = '',
                 active_entry = 0):
        h = 9
        w = min(max(34, max(len(help1), len(help2))+5), app.maxw-2)
        try:
            win = curses.newwin(h, w, int((app.maxh-h)/2)-1, int((app.maxw-w)/2))
            self.entry1 = EntryLine(w, h,
                                    int((app.maxh-h)/2) + 1,
                                    int((app.maxw-w+4) / 2),
                                    path1, with_historic1, with_complete1,
                                    panelpath1)
            self.entry2 = EntryLine(w, h,
                                    int((app.maxh-h)/2) + 4,
                                    int((app.maxw-w+4) / 2),
                                    path2, with_historic2, with_complete2,
                                    panelpath2)
            self.btns = Yes_No_Buttons(w, h, 2)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.bkgd(curses.color_pair(1))
        win.erase()
        win.box(0, 0)
        win.addstr(1, 2 , '%s:' % help1)
        win.addstr(4, 2 , '%s:' % help2)
        win.addstr(0, int((w-len(title)-2)/2), ' %s ' % title,
                   curses.color_pair(1) | curses.A_BOLD)
        win.refresh()

        self.with_historic = with_historic1 or with_historic2
        self.active_entry_i = active_entry
        if self.active_entry_i == 0:
            self.active_entry = self.entry1
        else:
            self.active_entry = self.entry2


    def run(self):
        # needed to avoid a problem with blank paths
        self.entry1.entry.refresh()
        self.entry2.entry.refresh()
        self.entry1.show()
        self.entry2.show()
        self.btns.show()
        cursor_show2()

        answer = True
        quit = False
        while not quit:
            self.btns.show()
            if self.active_entry_i in [0, 1]:
                ans = self.active_entry.manage_keys()
            else:
                ans = self.btns.manage_keys()
            if ans == -1:      # Ctrl-C
                quit = True
                answer = False
            elif ans == ord('\t'):     # tab
                self.active_entry_i += 1
                if self.active_entry_i > 3:
                    self.active_entry_i = 0
                if self.active_entry_i == 0:
                    self.active_entry = self.entry1
                    self.btns.active = 0
                    cursor_show2()
                elif self.active_entry_i == 1:
                    self.active_entry = self.entry2
                    self.btns.active = 0
                    cursor_show2()
                elif self.active_entry_i == 2:
                    self.btns.active = 1
                    cursor_hide()
                    answer = True
                else:
                    self.btns.active = 2
                    cursor_hide()
                    answer = False
            elif ans == 0x14:            # Ctrl-T
                # this is a hack, we need to return to refresh Entry
                return [self.entry1.text, self.entry2.text, self.active_entry_i]
            elif ans == 10:    # return values
                quit = True
                answer = True

        cursor_hide()
        if answer:
            # save new historic entries
            if self.with_historic:
                for text in self.entry1.text, self.entry2.text:
                    if text != None and text != '' and text != '*':
                        if len(historic) < 100:
                            historic.append(text)
                        else:
                            historic.reverse()
                            historic.pop()
                            historic.reverse()
                            historic.append(text)
            ans1, ans2 = self.entry1.text, self.entry2.text
        else:
            ans1, ans2 = None, None
        self.pwin.hide()
        return ans1, ans2


######################################################################
class SelectItem:
    """A window to select an item"""

    def __init__(self, entries, y0, x0, entry_i = ''):
        h = (app.maxh-1) - (y0+1) + 1
#         h = min(h, len(entries)+5)
        w = min(max(map(len, entries)), int(app.maxw/2)) + 4
        try:
            win = curses.newwin(h, w, y0, x0)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.keypad(1)
        cursor_hide()
        win.bkgd(curses.color_pair(4))
        self.entries = entries
        try:
            self.entry_i = self.entries.index(entry_i)
        except:
            self.entry_i = 0


    def show(self):
        win = self.pwin.window()
        win.erase()
        win.refresh()
        win.box(0, 0)
        y, x = win.getbegyx()
        h, w = win.getmaxyx()
        h0 = h - 2
        nels = len(self.entries)
        entry_a = int(self.entry_i/h0) * h0
        for i in xrange(h0):
            try:
                line = self.entries[entry_a + i]
            except IndexError:
                line = ''
            if len(line) > w - 3:
                if (w - 3) % 2 == 0:     # even
                    line = line[:int((w-3)/2)] + '~' + line[-int((w-3)/2)+2:]
                else:                    # odd
                    line = line[:int((w-3)/2)+1] + '~' + line[-int((w-3)/2)+2:]
            if line != '':
                win.addstr(i+1, 2, line, curses.color_pair(4))
        win.refresh()
        # cursor
        cursor = curses.newpad(1, w-1)
        cursor.bkgd(curses.color_pair(1))
        cursor.erase()
        line = self.entries[self.entry_i]
        if len(line) > w - 2:
            if (w - 2) % 2 == 0:         # even
                line = line[:int((w-2)/2)] + '~' + line[-int((w-2)/2)+2:]
            else:                        # odd
                line = line[:int((w-2)/2)+1] + '~' + line[-int((w-2)/2)+2:]
        cursor.addstr(0, 1, line, curses.color_pair(1) | curses.A_BOLD)
        y += 1; x += 1
        cur_row = y + self.entry_i % h0
        cursor.refresh(0, 0, cur_row, x, cur_row, x + w - 3)
        # scrollbar
        if nels > h0:
            n = max(int(h0*h0/nels), 1)
            y0 = min(max(int(int(self.entry_i/h0)*h0*h0/nels),0), h0 - n)
        else:
            y0 = n = 0
        win.vline(y0+1, w-1, curses.ACS_CKBOARD, n)
        if entry_a != 0:
            win.vline(1, w-1, '^', 1)
            if n == 1 and (y0 + 1 == 1):
                win.vline(2, w-1, curses.ACS_CKBOARD, n)
        if nels - 1 > entry_a + h0 - 1:
            win.vline(h0, w-1, 'v', 1)
            if n == 1 and (y0 == h0 - 1):
                win.vline(h0-1, w-1, curses.ACS_CKBOARD, n)


    def manage_keys(self):
        h, w = self.pwin.window().getmaxyx()
        nels = len(self.entries)
        while True:
            self.show()
            ch = self.pwin.window().getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):       # Ctrl-C, ESC
                return -1
            elif ch in (curses.KEY_UP, ord('k'), ord('K')):
                if self.entry_i != 0:
                    self.entry_i -= 1
            elif ch in (curses.KEY_DOWN, ord('j'), ord('J')):
                if self.entry_i != nels - 1:
                    self.entry_i += 1
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x08, 0x02):
                if self.entry_i < h - 3:
                    self.entry_i = 0
                else:
                    self.entry_i -= h - 2
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):
                if self.entry_i + (h-2) > nels - 1:
                    self.entry_i = nels - 1
                else:
                    self.entry_i += h - 2
            elif ch in (curses.KEY_HOME, 0x01):
                self.entry_i = 0
            elif ch in (curses.KEY_END, 0x05):
                self.entry_i = nels - 1
            elif ch == 0x13:     # Ctrl-S
                theentries = self.entries[self.entry_i:]
                ch2 = self.pwin.window().getkey()
                for e in theentries:
                    if e.find(ch2) == 0:
                        break
                else:
                    continue
                self.entry_i = self.entries.index(e)
            elif ch in (0x0A, 0x0D):   # enter
                return self.entries[self.entry_i]
            else:
                curses.beep()


    def run(self):
        selected = self.manage_keys()
        self.pwin.below().top()
        self.pwin.hide()
        return selected


######################################################################
class FindfilesWin:
    """A window to select a file"""

    def __init__(self, entries, entry_i = ''):
        y0 = 1
        h = (app.maxh-1) - (y0+1) + 1
        # w = max(map(len, entries)) + 4
        w = 64
        x0 = int((app.maxw-w) / 2)
        try:
            win = curses.newwin(h, w, y0, x0)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.keypad(1)
        cursor_hide()
        win.bkgd(curses.color_pair(4))
        self.entries = entries
        try:
            self.entry_i = self.entries.index(entry_i)
        except:
            self.entry_i = 0
        self.btn_active = 0


    def show(self):
        win = self.pwin.window()
        win.erase()
        win.refresh()
        win.box(0, 0)
        y, x = win.getbegyx()
        h, w = win.getmaxyx()
        h0 = h - 4
        nels = len(self.entries)
        entry_a = int(self.entry_i/h0) * h0
        for i in xrange(h0):
            try:
                line = self.entries[entry_a+i]
            except IndexError:
                line = ''
            if len(line) >= w - 3:
                if (w - 3) % 2 == 0:     # even
                    line = line[:int((w-3)/2)] + '~' + line[-int((w-3)/2)+3:]
                else:                    # odd
                    line = line[:int((w-3)/2)+1] + '~' + line[-int((w-3)/2)+3:]
            if line != '':
                win.addstr(i+1, 2, line, curses.color_pair(4))
        win.refresh()
        # cursor
        cursor = curses.newpad(1, w-2)
        cursor.attrset(curses.color_pair(1) | curses.A_BOLD)
        cursor.bkgdset(curses.color_pair(1))
        cursor.erase()
        line = self.entries[self.entry_i]
        if len(line) >= w - 3:
            if (w - 2) % 2 == 0:         # even
                line = line[:int((w-2)/2)] + '~' + line[-int((w-2)/2)+3:]
            else:                        # odd
                line = line[:int((w-2)/2)+1] + '~' + line[-int((w-2)/2)+3:]
        cursor.addstr(0, 1, line, curses.color_pair(1) | curses.A_BOLD)
        y += 1; x += 1
        cursor.refresh(0, 0, y + self.entry_i % h0,
                       x, y + self.entry_i % h0, x+w-3)
        # scrollbar
        if nels > h0:
            n = max(int(h0*h0/nels), 1)
            y0 = min(max(int(int(self.entry_i/h0)*h0*h0/nels),0), h0 - n)
        else:
            y0 = n = 0
        win.vline(y0+1, w-1, curses.ACS_CKBOARD, n)
        if entry_a != 0:
            win.vline(1, w-1, '^', 1)
            if n == 1 and (y0 + 1 == 1):
                win.vline(2, w-1, curses.ACS_CKBOARD, n)
        if nels - 1 > entry_a + h0 - 1:
            win.vline(h0, w-1, 'v', 1)
            if n == 1 and (y0 == h0 - 1):
                win.vline(h0-1, w-1, curses.ACS_CKBOARD, n)

        win.hline(h-3, 1, curses.ACS_HLINE, w-2)
        win.hline(h-3, 0, curses.ACS_LTEE, 1)
        win.hline(h-3, w-1, curses.ACS_RTEE, 1)
        win.addstr(h-2, 3,
                   '[ Go ]  [ Panelize ]  [ View ]  [ Edit ]  [ Do ]  [ Quit ]',
                   curses.color_pair(4))
        if self.btn_active == 0:
            attr0 = curses.color_pair(1) | curses.A_BOLD
            attr1 = attr2 = attr3 = attr4 = attr5 = curses.color_pair(4)
        elif self.btn_active == 1:
            attr1 = curses.color_pair(1) | curses.A_BOLD
            attr0 = attr2 = attr3 = attr4 = attr5 = curses.color_pair(4)
        elif self.btn_active == 2:
            attr2 = curses.color_pair(1) | curses.A_BOLD
            attr0 = attr1 = attr3 = attr4 = attr5 = curses.color_pair(4)
        elif self.btn_active == 3:
            attr3 = curses.color_pair(1) | curses.A_BOLD
            attr0 = attr1 = attr2 = attr4 = attr5 = curses.color_pair(4)
        elif self.btn_active == 4:
            attr4 = curses.color_pair(1) | curses.A_BOLD
            attr0 = attr1 = attr2 = attr3 = attr5 = curses.color_pair(4)
        else:
            attr5 = curses.color_pair(1) | curses.A_BOLD
            attr0 = attr1 = attr2 = attr3 = attr4 = curses.color_pair(4)
        win.addstr(h-2, 3, '[ Go ]', attr0)
        win.addstr(h-2, 11, '[ PAnelize ]', attr1)
        win.addstr(h-2, 25, '[ View ]', attr2)
        win.addstr(h-2, 35, '[ Edit ]', attr3)
        win.addstr(h-2, 45, '[ Do ]', attr4)
        win.addstr(h-2, 53, '[ Quit ]', attr5)
        win.refresh()


    def manage_keys(self):
        h, w = self.pwin.window().getmaxyx()
        nels = len(self.entries)
        while True:
            self.show()
            ch = self.pwin.window().getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):       # Ctrl-C, ESC
                return -1, None
            elif ch in (curses.KEY_UP, ord('k'), ord('K')):
                if self.entry_i != 0:
                    self.entry_i -= 1
            elif ch in (curses.KEY_DOWN, ord('j'), ord('j')):
                if self.entry_i != nels - 1:
                    self.entry_i += 1
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x08, 0x02):
                if self.entry_i < (h - 5):
                    self.entry_i = 0
                else:
                    self.entry_i -= (h - 4)
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):
                if self.entry_i + (h-4) > nels - 1:
                    self.entry_i = nels - 1
                else:
                    self.entry_i += (h - 4)
            elif ch in (curses.KEY_HOME, 0x01):
                self.entry_i = 0
            elif ch in (curses.KEY_END, 0x05):
                self.entry_i = nels - 1
            elif ch == 0x13:     # Ctrl-S
                theentries = self.entries[self.entry_i:]
                ch2 = self.pwin.window().getkey()
                for e in theentries:
                    if e.find(ch2) == 0:
                        break
                else:
                    continue
                self.entry_i = self.entries.index(e)
            elif ch == 0x09:        # tab
                if self.btn_active == 5:
                    self.btn_active = 0
                else:
                    self.btn_active += 1
            elif ch in (0x0A, 0x0D):   # enter
                if self.btn_active == 0:
                    return 0, self.entries[self.entry_i]
                elif self.btn_active == 1:
                    return 1, None
                elif self.btn_active == 2:
                    return 2, self.entries[self.entry_i]
                elif self.btn_active == 3:
                    return 3, self.entries[self.entry_i]
                elif self.btn_active == 4:
                    return 4, self.entries[self.entry_i]
                elif self.btn_active == 5:
                    return -1, None
            elif ch in (ord('a'), ord('A')):
                return 1, None
            elif ch in (curses.KEY_F3, ord('v'), ord('V')):
                return 2, self.entries[self.entry_i]
            elif ch in (curses.KEY_F4, ord('e'), ord('E')):
                return 3, self.entries[self.entry_i]
            elif ch in (ord('@'), ord('d'), ord('D')):
                return 4, self.entries[self.entry_i]
            else:
                curses.beep()


    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        return selected


######################################################################
class MenuWin:
    """A window to select a menu option"""

    def __init__(self, title, entries):
        h = len(entries) + 4
        w = max(map(len, entries)) + 4
        y0 = int((app.maxh-h) / 2)
        x0 = int((app.maxw-w) / 2)
        try:
            win = curses.newwin(h, w, y0, x0)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.keypad(1)
        cursor_hide()
        win.bkgd(curses.color_pair(3))
        self.title = title
        self.entries = entries
        self.entry_i = 0
        self.keys = [e[0] for e in entries]


    def show(self):
        win = self.pwin.window()
        win.erase()
        win.box(0, 0)
        y, x = win.getbegyx()
        h, w = win.getmaxyx()
        attr = curses.color_pair(7)
        win.addstr(0, int((w-len(self.title)-2)/2), ' %s ' % self.title, attr)
        for i in xrange(h-2):
            try:
                line = self.entries[i]
            except IndexError:
                line = ''
            if line != '':
                win.addstr(i+2, 2, line, curses.color_pair(3))
        win.refresh()
        # cursor
        cursor = curses.newpad(1, w-2)
        cursor.bkgd(curses.color_pair(1))
        cursor.erase()
        line = self.entries[self.entry_i]
        cursor.addstr(0, 1, line, curses.color_pair(1) | curses.A_BOLD)
        y += 1; x += 1
        cursor.refresh(0, 0, y + self.entry_i % (h-4) + 1,
                       x, y + self.entry_i % (h-4) + 1, x+w-3)


    def manage_keys(self):
        while True:
            self.show()
            ch = self.pwin.window().getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):       # Ctrl-C, ESC
                return -1
            elif ch in (curses.KEY_UP, ord('k'), ord('K')):
                if self.entry_i != 0:
                    self.entry_i -= 1
            elif ch in (curses.KEY_DOWN, ord('j'), ord('J')):
                if self.entry_i != len(self.entries) - 1:
                    self.entry_i += 1
            elif ch in (curses.KEY_HOME, 0x01, curses.KEY_PPAGE, 0x08, 0x02,
                        curses.KEY_BACKSPACE):
                self.entry_i = 0
            elif ch in (curses.KEY_END, 0x05, curses.KEY_NPAGE, ord(' '), 0x06):
                self.entry_i = len(self.entries) - 1
            elif ch == 0x13:     # Ctrl-S
                theentries = self.entries[self.entry_i:]
                ch2 = self.pwin.window().getkey()
                for e in theentries:
                    if e.find(ch2) == 0:
                        break
                else:
                    continue
                self.entry_i = self.entries.index(e)
            elif ch in (0x0A, 0x0D):   # enter
                return self.entries[self.entry_i]
            elif 0 <= ch <= 255 and chr(ch).lower() in self.keys:
                return self.entries[self.keys.index(chr(ch).lower())]
            else:
                curses.beep()


    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        return selected


######################################################################
class ChangePerms:
    """A window to change permissions, owner or group"""

    def __init__(self, file, fileinfo, i = 0, n = 0):
        h = 6 + 4
        w = 55 + 4
        y0 = int((app.maxh-h) / 2)
        x0 = int((app.maxw-w) / 2)
        try:
            win = curses.newwin(h, w, y0, x0)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        win.keypad(1)
        cursor_hide()
        win.bkgd(curses.color_pair(1))

        self.file = file
        self.perms_old = files.perms2str(fileinfo[files.FT_PERMS])
        self.perms = [l for l in self.perms_old]
        self.owner = fileinfo[files.FT_OWNER]
        self.group = fileinfo[files.FT_GROUP]
        self.owner_old = self.owner[:]
        self.group_old = self.group[:]
        self.i = i
        self.n = n
        self.entry_i = 0
        self.w = w


    def show_btns(self):
        win = self.pwin.window()
        h, w = win.getmaxyx()
        attr1 = curses.color_pair(1) | curses.A_BOLD
        attr2 = curses.color_pair(9) | curses.A_BOLD
        win.addstr(h-2, w-21, '[<Ok>]', attr1)
        win.addstr(h-2, w-13, '[ Cancel ]', attr1)
        if self.entry_i == 5:
            win.addstr(h-2, w-21, '[<Ok>]', attr2)
        elif self.entry_i == 6:
            win.addstr(h-2, w-13, '[ Cancel ]', attr2)
        if self.i:
            win.addstr(h-2, 3, '[ All ]', attr1)
            win.addstr(h-2, 12, '[ Ignore ]', attr1)
            if self.entry_i == 7:
                win.addstr(h-2, 3, '[ All ]', attr2)
            elif self.entry_i == 8:
                win.addstr(h-2, 12, '[ Ignore ]', attr2)


    def show(self):
        win = self.pwin.window()
        win.getmaxyx()
        win.erase()
        win.box(0, 0)
        attr = curses.color_pair(1) | curses.A_BOLD
        title = 'Change permissions, owner or group'
        win.addstr(0, int((self.w-len(title)-2)/2), ' %s ' % title, attr)
        win.addstr(2, 2, '\'%s\'' % self.file, attr)
        if self.i:
            win.addstr(2, self.w-12-2, '%4d of %-4d' % (self.i, self.n))
        win.addstr(4, 7, 'owner  group  other        owner         group')
        win.addstr(5, 2, 'new: [---]  [---]  [---]     [----------]  [----------]')
        win.addstr(6, 2, 'old: [---]  [---]  [---]     [----------]  [----------]')
        win.addstr(6, 8, self.perms_old[0:3])
        win.addstr(6, 15, self.perms_old[3:6])
        win.addstr(6, 22, self.perms_old[6:9])
        l = len(self.owner_old)
        if l > 10:
            owner = self.owner_old[:10]
        else:
            owner = self.owner_old + '-' * (10-l)
        win.addstr(6, 32, owner)
        l = len(self.group_old)
        if l > 10:
            group = self.group_old[:10]
        else:
            group = self.group_old + '-' * (10-l)
        win.addstr(6, 46, group)

        perms = ''.join(self.perms)
        win.addstr(5, 8, perms[0:3])
        win.addstr(5, 15, perms[3:6])
        win.addstr(5, 22, perms[6:9])
        l = len(self.owner)
        if l > 10:
            owner = self.owner[:10]
        else:
            owner = self.owner + '-' * (10-l)
        win.addstr(5, 32, owner)
        l = len(self.group)
        if l > 10:
            group = self.group[:10]
        else:
            group = self.group + '-' * (10-l)
        win.addstr(5, 46, group)
        if self.entry_i == 0:
            win.addstr(5, 8, perms[0:3],
                       curses.color_pair(5) | curses.A_BOLD)
        elif self.entry_i == 1:
            win.addstr(5, 15, perms[3:6],
                       curses.color_pair(5) | curses.A_BOLD)
        elif self.entry_i == 2:
            win.addstr(5, 22, perms[6:9],
                       curses.color_pair(5) | curses.A_BOLD)
        elif self.entry_i == 3:
            win.addstr(5, 32, owner,
                       curses.color_pair(5) | curses.A_BOLD)
        elif self.entry_i == 4:
            win.addstr(5, 46, group,
                       curses.color_pair(5) | curses.A_BOLD)
        self.show_btns()
        win.refresh()


    def manage_keys(self):
        y, x = self.pwin.window().getbegyx()
        while True:
            self.show()
            ch = self.pwin.window().getch()
            if ch in (0x03, 0x1B, ord('c'), ord('C'), ord('q'), ord('Q')):
                return -1
            elif ch in (ord('\t'), 0x09, curses.KEY_DOWN, curses.KEY_RIGHT):
                if self.i:
                    if self.entry_i == 4:
                        self.entry_i = 7
                    elif self.entry_i == 8:
                        self.entry_i = 5
                    elif self.entry_i == 6:
                        self.entry_i = 0
                    else:
                        self.entry_i += 1
                else:
                    if self.entry_i == 6:
                        self.entry_i = 0
                    else:
                        self.entry_i += 1
            elif ch in (curses.KEY_UP, curses.KEY_LEFT):
                if self.i:
                    if self.entry_i == 0:
                        self.entry_i = 6
                    elif self.entry_i == 5:
                        self.entry_i = 8
                    elif self.entry_i == 7:
                        self.entry_i = 4
                    else:
                        self.entry_i -= 1
                else:
                    if self.entry_i == 0:
                        self.entry_i = 6
                    else:
                        self.entry_i -= 1
            elif ch in (ord('r'), ord('R')):
                if not 0 <= self.entry_i <= 2:
                    continue
                d = self.entry_i * 3
                if self.perms[d] == 'r':
                    self.perms[d] = '-'
                else:
                    self.perms[d] = 'r'
            elif ch in (ord('w'), ord('W')):
                if not 0 <= self.entry_i <= 2:
                    continue
                d = 1 + self.entry_i * 3
                if self.perms[d] == 'w':
                    self.perms[d] = '-'
                else:
                    self.perms[d] = 'w'
            elif ch in (ord('x'), ord('X')):
                if not 0 <= self.entry_i <= 2:
                    continue
                d = 2 + self.entry_i * 3
                if self.perms[d] == 'x':
                    self.perms[d] = '-'
                else:
                    self.perms[d] = 'x'
            elif ch in (ord('t'), ord('T')):
                if not self.entry_i == 2:
                    continue
                if self.perms[8] == 't':
                    self.perms[8] = self.perms_old[8]
                else:
                    self.perms[8] = 't'
            elif ch in (ord('s'), ord('S')):
                if not 0 <= self.entry_i <= 1:
                    continue
                d = 2 + self.entry_i * 3
                if self.perms[d] == 's':
                    self.perms[d] = self.perms_old[d]
                else:
                    self.perms[d] = 's'
            elif ch in (0x0A, 0x0D):
                if self.entry_i == 3:
                    owners = files.get_owners()
                    owners.sort()
                    try:
                        owners.index(self.owner)
                    except:
                        owners.append(self.owner)
                    ret = SelectItem(owners, y+6, x+32, self.owner).run()
                    if ret != -1:
                        self.owner = ret
                    app.display()
                elif self.entry_i == 4:
                    groups = files.get_groups()
                    groups.sort()
                    try:
                        groups.index(self.group)
                    except:
                        groups.append(self.group)
                    ret = SelectItem(groups, y+6, x+32, self.group).run()
                    if ret != -1:
                        self.group = ret
                    app.display()
                elif self.entry_i == 6:
                    return -1
                elif self.i and self.entry_i == 7:
                    return self.perms, self.owner, self.group, 1
                elif self.i and self.entry_i == 8:
                    return 0
                else:
                    return self.perms, self.owner, self.group, 0
            elif self.i and ch in (ord('i'), ord('I')):
                return 0
            elif self.i and ch in (ord('a'), ord('A')):
                return self.perms, self.owner, self.group, 1
            else:
                curses.beep()


    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        return selected


######################################################################
##### some wrappers
def cursor_show2():
    try: # some terminals don't allow '2'
        curses.curs_set(2)
    except:
        cursor_show()


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


######################################################################
