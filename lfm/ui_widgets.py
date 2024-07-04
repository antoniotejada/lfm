# -*- coding: utf-8 -*-


import curses
import curses.panel
from os import sep, listdir
from os.path import basename, dirname, exists, expanduser, isdir, isabs, join

from utils import length, max_length, text2wrap, prev_step, next_step, perms2str, get_binary_programs, DirsTree
from common import *


########################################################################
##### Module variables
app = None
history = {}


########################################################################
##### Scrollbar
def display_scrollbar(win, y0, x0, h, n, i, a):
    """Display a scrollbar"""
    if n <= h:
        return
    win.vline(y0, x0, curses.ACS_VLINE, h)
    ss = max(h*h//n, 1)
    y = min(max((i//h)*h*h//n, 0), h-ss)
    win.vline(y0+y, x0, curses.ACS_CKBOARD, ss)
    if a != 0:
        win.vline(y0, x0, '^', 1)
        if (ss == 1) and (y == 0):
            win.vline(y0+1, x0, curses.ACS_CKBOARD, 1)
    if n > a + h:
        win.vline(y0+h-1, x0, 'v', 1)
        if (ss == 1) and (y == h-1):
            win.vline(y0+h-2, x0, curses.ACS_CKBOARD, 1)


######################################################################
##### Dialogs
def DialogMessage(title, subtitle):
    """Show a message. No wait, no keys"""
    title, subtitle = title[:app.w-14], subtitle[:app.w-14]
    h, w = 5, min(max(len(title), len(subtitle), 22)+6, app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog'])
    win.erase()
    win.box()
    win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
    win.addstr(2, 2, subtitle)
    win.addstr(h-1, (w-22)//2, ' Press Ctrl-C to stop ')
    win.refresh()


def DialogError(text):
    """Show an error message and waits for a key"""
    lines = text.split('\n')
    lth = max(max_length(lines), 31)
    h, w = min(len(lines)+4, app.h-2), min(lth+4, app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog_error'])
    win.erase()
    win.box()
    win.addstr(0, (w-7)//2, ' Error ', app.CLR['dialog_error_title'])
    win.addstr(h-1, (w-27)//2, ' Press any key to continue ')
    for i, l in enumerate(lines):
        win.addstr(i+2, 2, l, app.CLR['dialog_error_text'])
    win.refresh()
    while not win.getch():
        pass
    pwin.hide()
    curses.panel.update_panels()


def DialogGetKey(title, question):
    """Show a message and return key pressed"""
    question = question.replace('\t', ' ' * 4)
    lines = question.split('\n')
    h = min(len(lines)+4, app.h-2)
    w = min(max_length(lines)+4, app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog'])
    win.erase()
    win.box()
    win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
    for i, l in enumerate(lines):
        win.addstr(i+2, 2, l)
    win.refresh()
    win.keypad(1)
    while True:
        ch = win.getch()
        if ch in (0x03, 0x1B): # Ctrl-C, ESC
            ch = -1
            break
        elif 0x01 <= ch <= 0xFF:
            break
        else:
            curses.beep()
    pwin.hide()
    curses.panel.update_panels()
    return ch


def DialogConfirm(title, question, default=0):
    """Show a yes/no question, returning 1/0"""
    BTN_SELECTED, BTN_NO_SELECTED = app.CLR['button_active'], app.CLR['button_inactive']
    h, w = 5, min(max(34, len(question)+5), app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog'])
    win.erase()
    win.box()
    win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
    win.addstr(1, 2, question)
    win.refresh()
    row, col = (app.h-h)//2 + 3, (app.w-w)//2
    col1, col2 = col + w//5 + 1, col + w*4//5 - 6
    win.keypad(1)
    answer = default
    while True:
        if answer == 1:
            attr_yes, attr_no = BTN_SELECTED, BTN_NO_SELECTED
        else:
            attr_yes, attr_no = BTN_NO_SELECTED, BTN_SELECTED
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row+1, col1+6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col2, row+1, col2+5)
        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT, 9, curses.KEY_BTAB):
            answer = not answer
        elif ch in (ord('Y'), ord('y')):
            answer = 1
            break
        elif ch in (ord('N'), ord('n')):
            answer = 0
            break
        elif ch in (0x03, 0x1B):    # Ctrl-C, ESC
            answer = 0
            break
        elif ch in (10, 13):        # enter
            break
        else:
            curses.beep()
    pwin.hide()
    curses.panel.update_panels()
    return answer


def DialogConfirmAll(title, question, default=0):
    """Show a yes/all/no/stop question, returning 1/2/0/-1"""
    BTN_SELECTED, BTN_NO_SELECTED = app.CLR['button_active'], app.CLR['button_inactive']
    h, w = 5, min(max(48, len(question)+5), app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog'])
    win.erase()
    win.box()
    win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
    win.addstr(1, 2, question)
    win.refresh()
    row, col = (app.h-h)//2 + 3, (app.w-w)//2
    x = (w-28) // 5
    col1 = col + x + 1
    col2 = col1 + 7 + x
    col3 = col2 + 7 + x
    col4 = col3 + 6 + x
    win.keypad(1)
    answer = default
    order = [1, 2, 0, -1]
    while True:
        attr_yes = attr_all = attr_no = attr_skipall = BTN_NO_SELECTED
        if answer == 1:
            attr_yes = BTN_SELECTED
        elif answer == 2:
            attr_all = BTN_SELECTED
        elif answer == 0:
            attr_no = BTN_SELECTED
        else: # answer == -1:
            attr_skipall = BTN_SELECTED
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row+1, col1+6)
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ All ]', attr_all)
        btn.refresh(0, 0, row, col2, row+1, col2+6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col3, row+1, col3+5)
        btn = curses.newpad(1, 15)
        btn.addstr(0, 0, '[ Stop ]', attr_skipall)
        btn.refresh(0, 0, row, col4, row+1, col4+7)
        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_LEFT, curses.KEY_BTAB):
            try:
                answer = order[order.index(answer) - 1]
            except IndexError:
                answer = order[len(order)]
        elif ch in (curses.KEY_DOWN, curses.KEY_RIGHT, 9):
            try:
                answer = order[order.index(answer) + 1]
            except IndexError:
                answer = order[0]
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
    curses.panel.update_panels()
    return answer


def DialogConfirmAllNone(title, question, default=0):
    """Show a yes/all/no/none/stop question, returning 1/2/0/-2/-1"""
    BTN_SELECTED, BTN_NO_SELECTED = app.CLR['button_active'], app.CLR['button_inactive']
    h, w = 5, min(max(50, len(question)+5), app.w-2)
    try:
        win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
        pwin = curses.panel.new_panel(win)
        pwin.top()
    except curses.error:
        raise
    win.keypad(1)
    win.bkgd(app.CLR['dialog'])
    win.erase()
    win.box()
    win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
    win.addstr(1, 2, question)
    win.refresh()
    row, col = (app.h-h)//2 + 3, (app.w-w)//2
    x = (w-36) // 6
    col1 = col + x + 1
    col2 = col1 + 7 + x
    col3 = col2 + 7 + x
    col4 = col3 + 6 + x
    col5 = col4 + 8 + x
    win.keypad(1)
    answer = default
    order = [1, 2, 0, -2, -1]
    while True:
        attr_yes = attr_all = attr_no = attr_none = attr_skipall = BTN_NO_SELECTED
        if answer == 1:
            attr_yes = BTN_SELECTED
        elif answer == 2:
            attr_all = BTN_SELECTED
        elif answer == 0:
            attr_no = BTN_SELECTED
        elif answer == -2:
            attr_none = BTN_SELECTED
        else: # answer == -1:
            attr_skipall = BTN_SELECTED
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row+1, col1+6)
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ All ]', attr_all)
        btn.refresh(0, 0, row, col2, row+1, col2+6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col3, row+1, col3+5)
        btn = curses.newpad(1, 9)
        btn.addstr(0, 0, '[ NOne ]', attr_none)
        btn.refresh(0, 0, row, col4, row+1, col4+7)
        btn = curses.newpad(1, 9)
        btn.addstr(0, 0, '[ Stop ]', attr_skipall)
        btn.refresh(0, 0, row, col5, row+1, col5+7)
        ch = win.getch()
        if ch in (curses.KEY_UP, curses.KEY_LEFT, curses.KEY_BTAB):
            try:
                answer = order[order.index(answer) - 1]
            except IndexError:
                answer = order[len(order)]
        elif ch in (curses.KEY_DOWN, curses.KEY_RIGHT, 9):
            try:
                answer = order[order.index(answer) + 1]
            except IndexError:
                answer = order[0]
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
    curses.panel.update_panels()
    return answer


########################################################################
##### CursorAnimation
class CursorAnimation:
    """A small progress animation show on top-right corner of screen"""

    anim_chars = ('|', '/', '-', '\\')

    def __init__(self):
        self.step = 0
        self.win = curses.newpad(1, 2)
        self.win.bkgd(app.CLR['dialog_title'])

    def next(self):
        self.win.erase()
        self.win.addch(CursorAnimation.anim_chars[self.step%4])
        self.win.refresh(0, 0, 0, app.w-3, 1, app.w-2)
        self.step = 0 if self.step>3 else self.step+1


########################################################################
##### DialogMessagePane
class DialogMessagePanel:
    """A dialog to show a message. No wait"""

    def __init__(self, title, subtitle):
        title, subtitle = title[:app.w-14], subtitle[:app.w-14]
        h, w = 5, min(max(len(title), len(subtitle), 22)+6, app.w-2)
        try:
            win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
            self.pwin = curses.panel.new_panel(win)
            self.pwin.top()
        except curses.error:
            raise
        win.keypad(1)
        win.nodelay(1)
        win.bkgd(app.CLR['dialog'])
        win.erase()
        win.box()
        win.addstr(0, (w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
        win.addstr(2, 2, subtitle)
        win.addstr(h-1, (w-22)//2, ' Press Ctrl-C to stop ')
        win.refresh()

    def show(self):
        self.pwin.show()
        curses.panel.update_panels()

    def hide(self):
        self.pwin.hide()
        curses.panel.update_panels()

    def check_key(self):
        return self.pwin.window().getch()


########################################################################
##### DialogProgressXPanel
class DialogProgress1Panel:
    """A dialog with 1 progress bar"""

    def __init__(self, title):
        title = title[:app.w-14]
        h, self.w = 7, min(max(len(title), 60)+6, app.w-2)
        try:
            self.win = curses.newwin(h, self.w, (app.h-h)//2, (app.w-self.w)//2)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.nodelay(1)
        self.win.bkgd(app.CLR['dialog'])
        self.win.erase()
        self.win.box()
        self.win.addstr(0, (self.w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
        self.win.addstr(2, 2, 'File:')
        self.win.addstr(4, 2, ' '*(self.w-4-7), app.CLR['progressbar_bg'])
        self.win.addstr(4, self.w-8, '[  0%]')
        self.win.addstr(h-1, (self.w-22)//2, ' Press Ctrl-C to stop ')
        self.win.refresh()

    def show(self):
        self.pwin.show()
        curses.panel.update_panels()

    def hide(self):
        self.pwin.hide()
        curses.panel.update_panels()
        app.display()

    def check_key(self):
        return self.pwin.window().getch()

    def update(self, text, i, n):
        buf = '{}/{}'.format(i, n)
        self.win.addstr(2, 9, text2wrap(text, self.w-11-11, fill=True), app.CLR['dialog_title'])
        self.win.addstr(2, self.w-2-len(buf), buf)
        self.win.addstr(4, 2, ' '*int((self.w-4-7)*i/n), app.CLR['progressbar_fg'])
        self.win.addstr(4, self.w-8, '[{:3}%]'.format(100*i//n))


class DialogProgress2Panel(DialogProgress1Panel):
    """A dialog with 2 progress bar"""

    def __init__(self, title):
        title = title[:app.w-14]
        h, self.w = 8, min(max(len(title), 60)+6, app.w-2)
        try:
            self.win = curses.newwin(h, self.w, (app.h-h)//2, (app.w-self.w)//2)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.nodelay(1)
        self.win.bkgd(app.CLR['dialog'])
        self.win.erase()
        self.win.box()
        self.win.addstr(0, (self.w-len(title)-2)//2, ' %s ' % title, app.CLR['dialog_title'])
        self.win.addstr(2, 2, 'File:')
        self.win.addstr(4, 2, 'Bytes')
        self.win.addstr(4, 9, ' '*(self.w-4-14), app.CLR['progressbar_bg'])
        self.win.addstr(4, self.w-8, '[  0%]')
        self.win.addstr(5, 2, 'Count')
        self.win.addstr(5, 9, ' '*(self.w-4-14), app.CLR['progressbar_bg'])
        self.win.addstr(5, self.w-8, '[  0%]')
        self.win.addstr(h-1, (self.w-22)//2, ' Press Ctrl-C to stop ')
        self.win.refresh()

    def update(self, text, i, n, sp, st):
        buf = '{}/{}'.format(i, n)
        self.win.addstr(2, 9, text2wrap(text, self.w-11-11, fill=True), app.CLR['dialog_title'])
        self.win.addstr(2, self.w-2-len(buf), buf)
        self.win.addstr(4, 9, ' '*int((self.w-4-14)*sp/st), app.CLR['progressbar_fg'])
        self.win.addstr(4, self.w-8, '[{:3}%]'.format(100*sp//st))
        self.win.addstr(5, 9, ' '*int((self.w-4-14)*i/n), app.CLR['progressbar_fg'])
        self.win.addstr(5, self.w-8, '[{:3}%]'.format(100*i//n))


########################################################################
##### SelectItem
class SelectItem:
    """A dialog to select an item in a list"""

    def __init__(self, title, entries, y0=-1, x0=-1, entry_i='', quick_key=True, min_height=False):
        self.quick_key = quick_key
        if y0==-1 and x0==-1: # (y0,x0) is the position, if == -1 => center
            self.h = min(app.h-4, len(entries) if min_height else 10) + 2
            self.w = min(app.w-12, max(max_length(entries), len(title), 32)) + 8
            y0, x0 = (app.h-self.h) // 2, (app.w-self.w) // 2
        else:
            self.h = min(app.h-y0-2, 10) + 2 # len(entries) => no, fixed height
            self.w = max(min(app.w-2*x0-4-10, max_length(entries)), len(title), 20) + 8
        try:
            self.win = curses.newwin(self.h, self.w, y0, x0)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.bkgd(app.CLR['selectitem'])
        self.entries = entries
        self.nels = len(entries)
        try:
            self.entry_i = self.entries.index(entry_i)
        except:
            self.entry_i = 0
        self.title = title

    def show(self):
        self.win.erase()
        self.win.box()
        h0, w0 = self.h-2, self.w-4
        if self.title != '':
            self.win.addstr(0, (self.w-len(self.title)-2)//2, ' %s ' % self.title, app.CLR['selectitem_title'])
        entry_a = self.entry_i//h0 * h0
        for i in range(h0):
            if entry_a+i >= self.nels:
                break
            line = text2wrap(self.entries[entry_a+i], w0)
            if entry_a+i == self.entry_i:
                self.win.addstr(i+1, 2, line, app.CLR['selectitem_cursor'])
            else:
                self.win.addstr(i+1, 2, line)
        self.win.refresh()
        display_scrollbar(self.win, 1, self.w-1, h0, self.nels, self.entry_i, entry_a)

    def manage_keys(self):
        initials = {ord(e[0]) for e in self.entries}
        while True:
            self.show()
            ch = self.win.getch()
            if self.quick_key:
                if ch in initials:
                    for e in self.entries:
                        if ch == ord(e[0]):
                            return self.entries[self.entries.index(e)]
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):     # Ctrl-C, ESC
                return -1
            elif ch in (curses.KEY_UP, ord('k'), ord('K')):
                self.entry_i = max(0, self.entry_i-1)
            elif ch in (curses.KEY_DOWN, ord('j'), ord('J')):
                self.entry_i = min(self.entry_i+1, self.nels-1)
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x08, 0x02):
                self.entry_i = max(0, self.entry_i-(self.h-2))
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):
                self.entry_i = min(self.entry_i+(self.h-2), self.nels-1)
            elif ch in (curses.KEY_HOME, 0x01):
                self.entry_i = 0
            elif ch in (curses.KEY_END, 0x05):
                self.entry_i = self.nels - 1
            elif ch == 0x0C:     # Ctrl-L
                entry_a = int(self.entry_i//(self.h-2)) * (self.h-2)
                self.entry_i = entry_a + (self.h-2)//2
            elif ch == 0x13:     # Ctrl-S
                ch2 = self.win.getkey()
                for e in self.entries[self.entry_i:]:
                    if e.find(ch2) == 0:
                        self.entry_i = self.entries.index(e)
                        break
            elif ch in (0x0A, 0x0D):   # enter
                return self.entries[self.entry_i]
            else:
                curses.beep()

    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        curses.panel.update_panels()
        app.display()
        return selected


######################################################################
##### DialogFindGrep
class DialogFindGrep:
    """A dialog similar to SelectItem"""

    def __init__(self, title, entries, entry_i=''):
        self.h = min(app.h-8, len(entries), 12) + 5
        self.w = min(app.w-6, 100, max(max_length(entries), 60, len(title))) + 4
        y0, x0 = (app.h-self.h) // 2, (app.w-self.w) // 2
        try:
            self.win = curses.newwin(self.h, self.w, y0, x0)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.bkgd(app.CLR['selectitem'])
        self.entries = entries
        self.nels = len(entries)
        try:
            self.entry_i = self.entries.index(entry_i)
        except:
            self.entry_i = 0
        self.title = title
        self.btn_active = 0

    def show(self):
        BTN_SELECTED, BTN_NO_SELECTED = app.CLR['selectitem_cursor'], app.CLR['selectitem']
        self.win.erase()
        self.win.box()
        h0, w0 = self.h-4, self.w-4
        if self.title != '':
            self.win.addstr(0, (self.w-len(self.title)-2)//2, ' %s ' % self.title, app.CLR['selectitem_title'])
        entry_a = self.entry_i//h0 * h0
        for i in range(h0):
            if entry_a+i >= self.nels:
                break
            line = text2wrap(self.entries[entry_a+i], w0, start_pct=0.9)
            if entry_a+i == self.entry_i:
                self.win.addstr(i+1, 2, line, app.CLR['selectitem_cursor'])
            else:
                self.win.addstr(i+1, 2, line)
        display_scrollbar(self.win, 1, self.w-1, h0, self.nels, self.entry_i, entry_a)
        self.win.hline(self.h-3, 1, curses.ACS_HLINE, self.w-2)
        self.win.hline(self.h-3, 0, curses.ACS_LTEE, 1)
        self.win.hline(self.h-3, self.w-1, curses.ACS_RTEE, 1)
        self.win.addstr(self.h-2, 3, '[ Go ]  [ Panelize ]  [ View ]  [ Edit ]  [ Do ]  [ Quit ]', BTN_NO_SELECTED)
        attrs = [BTN_NO_SELECTED] * 6
        attrs[self.btn_active] = BTN_SELECTED
        self.win.addstr(self.h-2, 3, '[ Go ]', attrs[0])
        self.win.addstr(self.h-2, 11, '[ PAnelize ]', attrs[1])
        self.win.addstr(self.h-2, 25, '[ View ]', attrs[2])
        self.win.addstr(self.h-2, 35, '[ Edit ]', attrs[3])
        self.win.addstr(self.h-2, 45, '[ Do ]', attrs[4])
        self.win.addstr(self.h-2, 53, '[ Quit ]', attrs[5])
        self.win.refresh()

    def manage_keys(self):
        while True:
            self.show()
            ch = self.win.getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):     # Ctrl-C, ESC
                return -1, self.entries[self.entry_i]
            elif ch in (curses.KEY_UP, ord('k'), ord('K')):
                self.entry_i = max(0, self.entry_i-1)
            elif ch in (curses.KEY_DOWN, ord('j'), ord('J')):
                self.entry_i = min(self.entry_i+1, self.nels-1)
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x08, 0x02):
                self.entry_i = max(0, self.entry_i-(self.h-2))
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):
                self.entry_i = min(self.entry_i+(self.h-2), self.nels-1)
            elif ch in (curses.KEY_HOME, 0x01):
                self.entry_i = 0
            elif ch in (curses.KEY_END, 0x05):
                self.entry_i = self.nels - 1
            elif ch == 0x0C:     # Ctrl-L
                entry_a = int(self.entry_i//(self.h-2)) * (self.h-2)
                self.entry_i = entry_a + (self.h-2)//2
            elif ch == 0x13:     # Ctrl-S
                ch2 = self.win.getkey()
                for e in self.entries[self.entry_i:]:
                    if e.find(ch2) == 0:
                        self.entry_i = self.entries.index(e)
                        break
            elif ch in (curses.KEY_LEFT, curses.KEY_BTAB):
                self.btn_active = 5 if self.btn_active==0 else self.btn_active-1
            elif ch in (curses.KEY_RIGHT, 0x09): # tab
                self.btn_active = 0 if self.btn_active==5 else self.btn_active+1
            elif ch in (0x0A, 0x0D):   # enter
                return -1 if self.btn_active==5 else self.btn_active, self.entries[self.entry_i]
            elif ch in (ord('a'), ord('A')):
                return 1, self.entries[self.entry_i]
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
        curses.panel.update_panels()
        app.display()
        return selected


######################################################################
##### Helper widgets
class Yes_No_Buttons:
    """Yes/No buttons"""

    def __init__(self, w, h, d):
        self.row = (app.h-h)//2 + 4 + d
        col = (app.w-w)//2
        self.col1, self.col2 = col + w//5 + 1, col + w*4//5 - 6
        self.active = 0

    def show(self):
        BTN_SELECTED = app.CLR['button_active']
        BTN_NO_SELECTED = app.CLR['button_inactive']
        if self.active == 0:
            attr1, attr2 = BTN_NO_SELECTED, BTN_NO_SELECTED
        elif self.active == 1:
            attr1, attr2 = BTN_SELECTED, BTN_NO_SELECTED
        else:
            attr1, attr2 = BTN_NO_SELECTED, BTN_SELECTED
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[<Yes>]', attr1)
        btn.refresh(0, 0, self.row, self.col1, self.row + 1, self.col1 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr2)
        btn.refresh(0, 0, self.row, self.col2, self.row + 1, self.col2 + 5)

    def manage_keys(self):
        tmp = curses.newpad(1, 1)
        tmp.keypad(1)
        while True:
            ch = tmp.getch()
            if ch in (0x03, 0x1B):      # Ctrl-C, ESC
                return -1
            elif ch in (ord('\t'), curses.KEY_BTAB):
                return ch
            elif ch in (10, 13):        # enter
                if self.active == 1:
                    return 10
                else:
                    return -1
            else:
                curses.beep()


######################################################################
##### EntryLine
class EntryLine:
    """An entry line to enter a dir, a file, a pattern, etc"""

    def __init__(self, par_widget, w, y0, x0, text='', history=None, is_files=True, cli=False):
        try:
            self.win = curses.newwin(1, w+1, y0, x0)
        except curses.error:
            raise
        self.par_widget = par_widget
        self.color = app.CLR['powercli_text'] if cli else app.CLR['entryline']
        self.win.attrset(self.color)
        self.win.keypad(1)
        self.win.nodelay(0)
        self.x0, self.y0, self.w = x0, y0, w
        self.text, self.origtext, self.pos, self.ins = text, text, len(text), True
        self.history, self.history_i = history, -1 if history is None else len(history)
        self.cli = cli
        self.is_files = True if self.cli else is_files

    def show(self):
        text, pos, w, ltext = self.text, self.pos, self.w, len(self.text)
        if pos < w:
            relpos = pos
            textstr = text[:w] if ltext>w else text.ljust(w)
        else:
            if pos > ltext - (w-1):
                relpos = w-1 - (ltext-pos)
                textstr = text[ltext-w+1:] + ' '
            else:
                relpos = pos - pos//w*w
                textstr = text[pos//w*w:pos//w*w+w]
        # self.win.refresh()  # needed to avoid a problem with blank paths
        self.win.bkgd(app.CLR['dialog'])
        self.win.erase()
        self.win.addstr(textstr[:w], self.color)
        self.win.move(0, relpos)
        self.win.refresh()

    def __select_item(self, entries, pos0, title=''):
        if not entries:
            curses.beep()
            return
        elif len(entries) == 1:
            return entries.pop()
        else:
            x = self.x0+pos0 if self.x0+pos0<3*app.w//4-4 else self.x0+2
            if self.cli:
                y = app.h-14 # SelectItem has min 12 height, else: app.h//2-2
            else:
                y = self.y0
            curses.curs_set(0)
            selected = SelectItem(title, entries, y+1, x-2, quick_key=False).run()
            app.display()
            if not self.cli:
                self.par_widget.show()
            curses.curs_set(1)
            return selected

    def __get_list_completion(self, text):
        tab_path = app.pane_active.tab_active.fs.pdir
        path = expanduser(text)
        path = path if isabs(path) else join(tab_path, path)
        try:
            if text.endswith(os.sep) and isdir(path):
                basedir, fs = path, listdir(path)
            else:
                basedir, start = dirname(path), basename(path)
                fs = [f for f in listdir(basedir) if f.startswith(start)]
        except OSError:
            return basedir, list()
        # sort files with dirs first
        d1, d2 = list(), list()
        for f in fs:
            if isdir(join(basedir, f)):
                d1.append(f+sep)
            else:
                d2.append(f)
        d1.sort()
        d1.extend(sorted(d2))
        return basedir, d1

    def manage_keys(self):
        while True:
            self.show()
            wch = self.win.get_wch()
            if isinstance(wch, str) and ord(wch)>=32 and ord(wch)!=127:
                if self.ins:
                    self.text = self.text[:self.pos] + wch + self.text[self.pos:]
                else:
                    self.text = self.text[:self.pos] + wch + self.text[self.pos+1:]
                self.pos += 1
            else: # int!
                wch = ord(wch) if isinstance(wch, str) else wch
                if wch in (3, 21):                       # C-c, ESC
                    return -1
                if wch == 24 and self.cli:               # C-x
                    return -2
                elif wch in (9, curses.KEY_BTAB) and not self.cli: # tab, S-tab
                    return wch
                elif wch in (10, 13):                    # enter
                    return 10
                # movement
                elif wch in (curses.KEY_HOME, 1):        # home, C-a
                    self.pos = 0
                elif wch in (curses.KEY_END, 5):         # end, C-e
                    self.pos = len(self.text)
                elif wch in (curses.KEY_LEFT, 2):        # left, C-b
                    if self.pos > 0:
                        self.pos -= 1
                elif wch in (curses.KEY_RIGHT, 6):       # right, C-f
                    if self.pos < len(self.text):
                        self.pos += 1
                elif wch in (16, 0x222, 0x223, 0x224):                 # C-p, C-left
                    self.pos = prev_step(self.text, self.pos)
                elif wch in (14, 0x231, 0x232, 0x233):                 # C-n, C-right
                    self.pos = next_step(self.text, self.pos)
                # deletion
                elif wch in (127, curses.KEY_BACKSPACE): # Backspace
                    if len(self.text) > 0 and self.pos > 0:
                        self.text = self.text[:self.pos-1] + self.text[self.pos:]
                        self.pos -= 1
                elif wch in (17, ):                      # C-q, C-Backspace
                    pos = prev_step(self.text, self.pos)
                    self.text = self.text[:pos] + self.text[self.pos:]
                    self.pos = pos
                elif wch == curses.KEY_DC:               # Del
                    if self.pos < len(self.text):
                        self.text = self.text[:self.pos] + self.text[self.pos+1:]
                elif wch in (18, 0x208, 0x209):                 # C-r, C-Del
                    pos = next_step(self.text, self.pos)
                    if pos>0 and self.text[pos-1] in '.([{<"\'':
                        pos = max(0, pos-1)
                    if pos+1<len(self.text) and self.text[pos] in ' ':
                        pos += 1
                    self.text = self.text[:self.pos] + self.text[pos:]
                elif wch == 23:                          # C-w
                    self.text, self.pos = '', 0
                elif wch == 8:                           # C-h
                    self.text, self.pos = self.text[self.pos:], 0
                elif wch == 11:                          # C-k
                    self.text = self.text[:self.pos]
                # insertion
                elif wch == 26:                          # C-z
                    self.text, self.pos = self.origtext, len(self.origtext)
                elif wch == 22:                          # C-v
                    if self.is_files:
                        buf = app.pane_active.tab_active.current_filename
                        buf = '"{}"'.format(buf) if self.cli else buf
                        self.text = self.text[:self.pos] + buf + self.text[self.pos:]
                        self.pos += len(buf)
                elif wch == 19:                          # C-s
                    if self.is_files:
                        buf = app.pane_active.tab_active.dirname + sep
                        buf = '"{}"'.format(buf) if self.cli else buf
                        self.text = self.text[:self.pos] + buf + self.text[self.pos:]
                        self.pos += len(buf)
                elif wch == 15:                          # C-o
                    if self.is_files:
                        buf = app.pane_inactive.tab_active.dirname + sep
                        buf = '"{}"'.format(buf) if self.cli else buf
                        self.text = self.text[:self.pos] + buf + self.text[self.pos:]
                        self.pos += len(buf)
                elif wch in (4, 28):                     # C-d, C-\
                    if self.is_files:
                        bmks = [app.cfg.bookmarks[k] for k in sorted(app.cfg.bookmarks.keys())]
                        selected = self.__select_item(bmks, self.pos if self.cli else 0, 'Bookmarks')
                        if selected not in (None, -1, ''):
                            if self.cli:
                                self.text = self.text[:self.pos] + '"' + selected + '"' + self.text[self.pos:]
                                self.pos += len(selected)+2
                            else:
                                self.text, self.pos = selected, len(selected)
                elif wch == 25:                          # C-y
                    if self.is_files:
                        items = app.pane_active.tab_active.history[::-1]
                        items += [p for p in app.pane_inactive.tab_active.history[::-1] if p not in items]
                        if items:
                            selected = self.__select_item(items, self.pos if self.cli else 0, 'Previous paths')
                            if selected not in (None, -1, ''):
                                if self.cli:
                                    self.text = self.text[:self.pos] + '"' + selected + '"' + self.text[self.pos:]
                                    self.pos += len(selected)+2
                                else:
                                    self.text, self.pos = selected, len(selected)
                elif wch == 20 and not self.cli:         # C-t
                    if self.is_files:
                        basedir, entries = self.__get_list_completion(self.text)
                        selected = self.__select_item(entries, self.pos, 'Complete')
                        if selected not in (None, -1, ''):
                            basepath = app.pane_active.tab_active.fs.pdir + os.sep
                            self.text = join(basedir, selected)
                            if self.text.startswith(basepath):
                                self.text = join(basedir, selected)[len(basepath):]
                            self.pos = len(self.text)
                elif wch in (9, 20) and self.cli:        # tab, C-t
                    if self.text.rfind(' "', 0, self.pos) != -1:
                        pos1 = self.pos-1 if self.text[self.pos-1]=='"' else self.pos
                        pos0 = self.text.rfind(' "', 0, pos1) + 2
                    else:
                        pos0 = self.text.rfind(' ', 0, self.pos) + 1
                        pos1 = self.pos
                    text = self.text[pos0:pos1]
                    if pos0 == 0:
                        basedir, entries = None, [p for p in get_binary_programs() if p.startswith(text)]
                    else:
                        basedir, entries = self.__get_list_completion(text)
                    selected = self.__select_item(entries, pos0, 'Complete')
                    if selected is not None and selected != -1:
                        if basedir is None:
                            selected += ' '
                        else:
                            if basedir != app.pane_active.tab_active.fs.pdir:
                                selected = join(basedir, selected)
                        self.text = self.text[:pos0] + selected + self.text[pos1:]
                        self.pos = len(self.text[:pos0]+selected)
                # history
                elif wch == curses.KEY_UP:               # up
                    if self.history is not None and self.history_i > 0:
                        if self.history_i == len(self.history):
                            self.history.append(self.text)
                        self.history_i -= 1
                        self.text = self.history[self.history_i]
                        self.pos = len(self.text)
                elif wch == curses.KEY_DOWN:             # down
                    if self.history is not None and self.history_i < len(self.history)-1:
                            self.history_i += 1
                            self.text = self.history[self.history_i]
                            self.pos = len(self.text)
                elif wch == 7:                           # C-g
                    if self.cli:
                        BOOKMARKS_STR, HISTORY_STR = '----- Stored:  -----', '----- History: -----'
                        entries = [BOOKMARKS_STR]
                        entries.extend([c for c in app.cfg.powercli_favs if c.strip()])
                        entries.append(HISTORY_STR)
                        entries.extend([c for c in self.history if c.strip()])
                        selected = self.__select_item(entries, 0, 'History')
                        if selected not in (None, -1, '', BOOKMARKS_STR, HISTORY_STR):
                            self.text, self.pos = selected, len(selected)
                    else:
                        if self.history is not None and len(self.history) > 0:
                            selected = self.__select_item(self.history, 0, 'History')
                            if selected not in (None, -1):
                                self.text, self.pos = selected, len(selected)
                # other
                elif wch == curses.KEY_IC:               # insert
                    self.ins = not self.ins
                else:
                    curses.beep()


######################################################################
##### DialogEntry
class DialogEntry:
    """An entry dialog to enter a dir, a file, a pattern…"""

    def __init__(self, title, help, text='', history=None, is_files=True):
        h, w = 6, max(len(help)+5, app.w//2)
        try:
            self.win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
            self.entry = EntryLine(self, w-4, (app.h-h)//2+2, (app.w-w+4)//2, text,
                                   history=history, is_files=is_files, cli=False)
            self.btns = Yes_No_Buttons(w, h, 0)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.w, self.title, self.help = w, title, help
        self.win.keypad(1)
        self.win.bkgd(app.CLR['dialog'])
        self.active_widget = self.entry

    def show(self):
        self.win.erase()
        self.win.box()
        self.win.addstr(0, (self.w-len(self.title)-2)//2, ' %s ' % self.title, app.CLR['dialog_title'])
        self.win.addstr(1, 2, '%s:' % self.help)
        self.win.refresh()
        self.entry.show()
        self.btns.show()

    def run(self):
        self.show()
        curses.curs_set(1)
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
                    curses.curs_set(0)
                    answer = self.entry.text
                elif self.active_widget == self.btns and self.btns.active == 1:
                    self.btns.active = 2
                    curses.curs_set(0)
                    answer = None
                else:
                    self.active_widget = self.entry
                    self.btns.active = 0
                    curses.curs_set(1)
            elif ans == curses.KEY_BTAB:     # S+tab
                if self.active_widget == self.entry:
                    self.active_widget = self.btns
                    self.btns.active = 2
                    curses.curs_set(0)
                    answer = None
                elif self.active_widget == self.btns and self.btns.active == 1:
                    self.active_widget = self.entry
                    self.btns.active = 0
                    curses.curs_set(1)
                else:
                    self.active_widget = self.btns
                    self.btns.active = 1
                    curses.curs_set(0)
                    answer = self.entry.text
            elif ans == 10:              # return values
                quit = True
                answer = self.entry.text.strip()
        curses.curs_set(0)
        self.pwin.hide()
        curses.panel.update_panels()
        app.display()
        return answer


class DialogDoubleEntry:
    """A dialog with 2 entries"""

    def __init__(self, title, help1, help2, text1, text2='', history1=None, history2=None, is_files=True):
        h, w = 9, max(len(help2)+5, app.w//2)
        try:
            self.win = curses.newwin(h, w, (app.h-h)//2, (app.w-w)//2)
            self.entry1 = EntryLine(self, w-4, (app.h-h)//2+2, (app.w-w+4)//2, text1,
                                    history=history1, is_files=is_files, cli=False)
            self.entry2 = EntryLine(self, w-4, (app.h-h)//2+5, (app.w-w+4)//2, text2,
                                    history=history2, is_files=is_files, cli=False)
            self.btns = Yes_No_Buttons(w, h, 3)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.w, self.title, self.help1, self.help2 = w, title, help1, help2
        self.win.keypad(1)
        self.win.bkgd(app.CLR['dialog'])
        self.active_widget = self.entry1

    def show(self):
        self.win.erase()
        self.win.box()
        self.win.addstr(0, (self.w-len(self.title)-2)//2, ' %s ' % self.title, app.CLR['dialog_title'])
        self.win.addstr(1, 2, '%s:' % self.help1)
        self.win.addstr(4, 2, '%s:' % self.help2)
        self.win.refresh()
        self.entry1.show()
        self.entry2.show()
        self.btns.show()

    def run(self):
        self.show()
        curses.curs_set(1)
        quit = False
        while not quit:
            self.btns.show()
            ans = self.active_widget.manage_keys()
            if ans == -1:              # Ctrl-C
                quit = True
                answer = None
            elif ans == ord('\t'):     # tab
                if self.active_widget == self.entry1:
                    self.active_widget = self.entry2
                elif self.active_widget == self.entry2:
                    self.active_widget = self.btns
                    self.btns.active = 1
                    curses.curs_set(0)
                    answer = self.entry1.text, self.entry2.text
                elif self.active_widget == self.btns and self.btns.active == 1:
                    self.btns.active = 2
                    answer = None
                else:
                    self.active_widget = self.entry1
                    self.btns.active = 0
                    curses.curs_set(1)
            elif ans == curses.KEY_BTAB:     # S+tab
                if self.active_widget == self.entry1:
                    self.active_widget = self.btns
                    self.btns.active = 2
                    curses.curs_set(0)
                    answer = None
                elif self.active_widget == self.entry2:
                    self.active_widget = self.entry1
                elif self.active_widget == self.btns and self.btns.active == 1:
                    self.active_widget = self.entry2
                    self.btns.active = 0
                    curses.curs_set(1)
                    answer = self.entry1.text, self.entry2.text
                else:
                    self.btns.active = 1
                    answer = self.entry1.text, self.entry2.text
            elif ans == 10:              # return values
                quit = True
                answer = self.entry1.text.strip(), self.entry2.text.strip()
        curses.curs_set(0)
        self.pwin.hide()
        curses.panel.update_panels()
        app.display()
        return answer


########################################################################
##### DialogPerms & DialogOwner
class DialogPerms:
    """Dialog to change file permissions"""

    def __init__(self, filename, perms, i=0, n=0):
        self.h, self.w = 7+4, 42+4
        x0, y0 = int((app.w-self.w)/2), int((app.h-self.h)/2)
        try:
            self.win = curses.newwin(self.h, self.w, y0, x0)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.bkgd(app.CLR['dialog'])
        self.file = filename
        self.perms_old = perms2str(perms)
        self.perms = [l for l in self.perms_old]
        self.recursive = False
        self.i, self.n, self.entry_i = i, n, 0

    def show_btns(self):
        attr_sel, attr_no = app.CLR['button_active'], app.CLR['button_inactive']
        self.win.addstr(self.h-2, self.w-21, '[<Ok>]', attr_sel if self.entry_i==11 else attr_no)
        self.win.addstr(self.h-2, self.w-13, '[ Cancel ]', attr_sel if self.entry_i==12 else attr_no)
        if self.n > 1:
            self.win.addstr(self.h-2, 3, '[ All ]', attr_sel if self.entry_i==13 else attr_no)
            self.win.addstr(self.h-2, 12, '[ Ignore ]', attr_sel if self.entry_i==14 else attr_no)

    def show(self):
        self.win.erase()
        self.win.box()
        attr, attr_sel, attr_no = app.CLR['dialog_title'], app.CLR['dialog_perms'], app.CLR['dialog']
        title = 'Change file(s) permissions'
        self.win.addstr(0, int((self.w-len(title)-2)/2), ' {} '.format(title), attr)
        if self.n > 1:
            buf = '{}/{}'.format(self.i, self.n)
            lbuf = len(buf)
            self.win.addstr(2, self.w-2-len(buf), buf)
        else:
            lbuf = 0
        self.win.addstr(2, 2, 'File:')
        self.win.addstr(2, 8, text2wrap(self.file, self.w-11-lbuf, fill=True), attr)
        self.win.addstr(4, 2, '      owner  group  other        recursive')
        self.win.addstr(5, 2, 'new:  [---]  [---]  [---]           [ ]')
        self.win.addstr(6, 2, 'old:  [---]  [---]  [---]           [ ]')
        perms = ''.join(self.perms)
        self.win.addstr(5, 9, perms[0:3], attr_sel if self.entry_i==0 else attr_no)
        self.win.addstr(5, 16, perms[3:6], attr_sel if self.entry_i==1 else attr_no)
        self.win.addstr(5, 23, perms[6:9], attr_sel if self.entry_i==2 else attr_no)
        self.win.addstr(5, 39, 'X' if self.recursive else ' ', attr_sel if self.entry_i==3 else attr_no)
        self.win.addstr(6, 9, self.perms_old[0:3])
        self.win.addstr(6, 16, self.perms_old[3:6])
        self.win.addstr(6, 23, self.perms_old[6:9])
        self.show_btns()
        self.win.refresh()

    def manage_keys(self):
        order = [0, 1, 2, 3, 13, 14, 11, 12] if self.n>1 else [0, 1, 2, 3, 11, 12]
        nels = len(order)
        while True:
            self.show()
            ch = self.win.getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):
                return -1, False, False
            elif ch in (ord('\t'), 0x09, curses.KEY_DOWN, curses.KEY_RIGHT):
                i = order.index(self.entry_i)
                self.entry_i = order[0 if i==nels-1 else i+1]
            elif ch in (curses.KEY_UP, curses.KEY_LEFT, curses.KEY_BTAB):
                i = order.index(self.entry_i)
                self.entry_i = order[nels-1 if i==0 else i-1]
            elif ch in (ord('r'), ord('R')):
                if 0 <= self.entry_i <= 2:
                    d = self.entry_i * 3
                    self.perms[d] = 'r' if self.perms[d]=='-' else '-'
            elif ch in (ord('w'), ord('W')):
                if 0 <= self.entry_i <= 2:
                    d = 1 + self.entry_i * 3
                    self.perms[d] = 'w' if self.perms[d]=='-' else '-'
            elif ch in (ord('x'), ord('X')):
                if 0 <= self.entry_i <= 2:
                    d = 2 + self.entry_i * 3
                    self.perms[d] = 'x' if self.perms[d]=='-' else '-'
            elif ch in (ord('t'), ord('T')):
                if self.entry_i == 2:
                    self.perms[8] = 't' if self.perms[8]=='-' else '-'
            elif ch in (ord('s'), ord('S')):
                if 0 <= self.entry_i <= 1:
                    d = 2 + self.entry_i * 3
                    self.perms[d] = 's' if self.perms[d]=='-' else '-'
            elif ch in (ord(' '), 0x0A, 0x0D):
                if self.entry_i == 3:
                    self.recursive = not self.recursive
                elif self.entry_i == 12:
                    return -1, False, False
                elif self.n>1 and self.entry_i==13:
                    return self.perms, self.recursive, True
                elif self.n>1 and self.entry_i==14:
                    return 0, False, False
                else:
                    return self.perms, self.recursive, False
            elif ch in (ord('i'), ord('I')): # and self.n>1
                return 0, False, False
            elif ch in (ord('a'), ord('A')): # and self.n>1
                return self.perms, self.recursive, True
            else:
                curses.beep()

    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        curses.panel.update_panels()
        return selected


class DialogOwner:
    """Dialog to change file owner/group"""

    def __init__(self, filename, owner, group, owners, groups, i=0, n=0):
        self.h, self.w = 7+4, 45+4
        x0, y0 = int((app.w-self.w)/2), int((app.h-self.h)/2)
        try:
            self.win = curses.newwin(self.h, self.w, y0, x0)
            self.pwin = curses.panel.new_panel(self.win)
            self.pwin.top()
        except curses.error:
            raise
        self.win.keypad(1)
        self.win.bkgd(app.CLR['dialog'])
        self.file = filename
        self.owner = self.owner_old = owner
        self.group = self.group_old = group
        self.owners, self.groups = owners, groups
        self.recursive = True
        self.i, self.n, self.entry_i = i, n, 0

    def show_btns(self):
        attr_sel, attr_no = app.CLR['button_active'], app.CLR['button_inactive']
        self.win.addstr(self.h-2, self.w-21, '[<Ok>]', attr_sel if self.entry_i==11 else attr_no)
        self.win.addstr(self.h-2, self.w-13, '[ Cancel ]', attr_sel if self.entry_i==12 else attr_no)
        if self.n > 1:
            self.win.addstr(self.h-2, 3, '[ All ]', attr_sel if self.entry_i==13 else attr_no)
            self.win.addstr(self.h-2, 12, '[ Ignore ]', attr_sel if self.entry_i==14 else attr_no)

    def __fmt_text(self, text, n=10, ch='-'):
        l = len(text)
        return text[:n] if l>n else text+ch*(n-l)

    def show(self):
        self.win.erase()
        self.win.box()
        attr, attr_sel, attr_no = app.CLR['dialog_title'], app.CLR['dialog_perms'], app.CLR['dialog']
        title = 'Change file(s) owner/group'
        self.win.addstr(0, int((self.w-len(title)-2)/2), ' {} '.format(title), attr)
        if self.n > 1:
            buf = '{}/{}'.format(self.i, self.n)
            lbuf = len(buf)
            self.win.addstr(2, self.w-2-len(buf), buf)
        else:
            lbuf = 0
        self.win.addstr(2, 2, 'File:')
        self.win.addstr(2, 8, text2wrap(self.file, self.w-11-lbuf, fill=True), attr)
        self.win.addstr(4, 2, '          owner         group       recursive')
        self.win.addstr(5, 2, 'new:  [----------]  [----------]       [ ]')
        self.win.addstr(6, 2, 'old:  [----------]  [----------]       [ ]')
        self.win.addstr(5, 9, self.__fmt_text(self.owner), attr_sel if self.entry_i==0 else attr_no)
        self.win.addstr(5, 23, self.__fmt_text(self.group), attr_sel if self.entry_i==1 else attr_no)
        self.win.addstr(5, 42, 'X' if self.recursive else ' ', attr_sel if self.entry_i==3 else attr_no)
        self.win.addstr(6, 9, self.owner_old)
        self.win.addstr(6, 23, self.group_old)
        self.show_btns()
        self.win.refresh()

    def manage_keys(self):
        y, x = self.pwin.window().getbegyx()
        order = [0, 1, 3, 13, 14, 11, 12] if self.n>1 else [0, 1, 3, 11, 12]
        nels = len(order)
        while True:
            self.show()
            ch = self.win.getch()
            if ch in (0x03, 0x1B, ord('q'), ord('Q')):
                return -1, -1, False, False
            elif ch in (ord('\t'), 0x09, curses.KEY_DOWN, curses.KEY_RIGHT):
                i = order.index(self.entry_i)
                self.entry_i = order[0 if i==nels-1 else i+1]
            elif ch in (curses.KEY_UP, curses.KEY_LEFT, curses.KEY_BTAB):
                i = order.index(self.entry_i)
                self.entry_i = order[nels-1 if i==0 else i-1]
            elif ch in (ord(' '), 0x0A, 0x0D):
                if self.entry_i == 3:
                    self.recursive = not self.recursive
                elif self.entry_i == 0:
                    ret = SelectItem('Select new owner', self.owners, y+6, x+7, self.owner).run()
                    if ret != -1:
                        self.owner = ret
                elif self.entry_i == 1:
                    ret = SelectItem('Select new group', self.groups, y+6, x+21, self.group).run()
                    if ret != -1:
                        self.group = ret
                elif self.entry_i == 12:
                    return -1, -1, False, False
                elif self.n>1 and self.entry_i==13:
                    return self.owner, self.group, self.recursive, True
                elif self.n>1 and self.entry_i==14:
                    return 0, 0, False, False
                else:
                    return self.owner, self.group, self.recursive, False
            elif ch in (ord('i'), ord('I')): # and self.n>1
                return 0, 0, False, False
            elif ch in (ord('a'), ord('A')): # and self.n>1
                return self.owner, self.group, self.recursive, True
            else:
                curses.beep()

    def run(self):
        selected = self.manage_keys()
        self.pwin.hide()
        curses.panel.update_panels()
        return selected


########################################################################
##### TreeView
class TreeView:
    """TreeView class"""

    def __init__(self, path=sep):
        if not exists(path) or not isdir(path):
            raise ValueError('Path does not exist or is not dir: "{}"'.format(path))
        if path[-1] == sep and path != sep:
            path = path[:-1]
        self.path = path
        self.tree = DirsTree(path, app.cfg.options.show_dotfiles)
        self.__init_ui()

    def __init_ui(self):
        """initialize curses stuff"""
        self.__calculate_dims()
        try:
            self.win = curses.newwin(*self.dims)
        except curses.error:
            raise
        self.win.keypad(1)
        if curses.has_colors():
            self.win.bkgd(app.CLR['files_reg'])

    def __calculate_dims(self):
        if app.pane_active.mode == PaneMode.half:
            win = app.pane_inactive.win
        elif app.pane_active.mode == PaneMode.full:
            win = app.pane_active.win
        h, w = win.getmaxyx()
        y0, x0 = win.getbegyx()
        self.dims = h, w, y0, x0

    def display(self):
        h, n = app.h-4, len(self.tree)
        j, a, z = 0, self.tree.pos//h * h, (self.tree.pos//h+1) * h
        self.win.erase()
        self.win.attrset(app.CLR['pane_active'])
        self.win.box()
        display_scrollbar(self.win, 1, self.dims[1]-1, h, n, a, a)
        self.win.addstr(0, 2, ' Tree ', app.CLR['pane_header_path'])
        self.win.attrset(app.CLR['files_reg'])
        if z > n:
            a, z = max(n-h, 0), n
        for i in range(a, z):
            j += 1
            name, depth, fullname = self.tree[i]
            if name == sep:
                self.win.addstr(j, 1, ' ')
            else:
                self.win.move(j, 1)
                for kk in range(depth):
                    self.win.addstr(' ')
                    self.win.addch(curses.ACS_VLINE) # \u2502
                    self.win.addstr(' ')
                self.win.addstr(' ')
                if i == n-1:
                    self.win.addch(curses.ACS_LLCORNER) # \u2514
                elif depth > self.tree.get_depth(i+1):
                    self.win.addch(curses.ACS_LLCORNER) # \u2514
                else:
                    self.win.addch(curses.ACS_LTEE) # \u251C
                self.win.addch(curses.ACS_HLINE) # \u2500
                self.win.addstr(' ')
            w, wd = app.w//2-2, 3*depth+4
            if fullname == self.path:
                self.win.addstr(text2wrap(name, w-wd-3, fill=False), app.CLR['cursor'])
                if self.tree.has_children_dirs:
                    self.win.addstr(' \u27A9') # ' ->'
            else:
                self.win.addstr(text2wrap(name, w-wd, fill=False))
        app.statusbar.show_message('Path: {}'.format(self.path))

    def run(self):
        while True:
            self.display()
            chext = 0
            ch = self.win.getch()
            # to avoid extra chars input
            if ch == 0x1B:
                chext = 1
                ch = self.win.getch()
                ch = self.win.getch()
            if ch in (ord('k'), ord('K'), curses.KEY_UP):
                if self.tree.pos == 0 or self.tree.is_first_sibling:
                    continue
                newpos = self.tree.pos - 1
            elif ch in (ord('j'), ord('j'), curses.KEY_DOWN):
                if self.tree.pos == len(self.tree)-1 or self.tree.is_last_sibling:
                    continue
                newpos = self.tree.pos + 1
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x02):
                if self.tree.pos-(app.h-4) >= 0:
                    if self.tree.cur_depth == self.tree.get_depth(self.tree.pos-(app.h-4)):
                        newpos = self.tree.pos-(app.h-4)
                    else:
                        newpos = self.tree.first_sibling_pos
                else:
                    newpos = self.tree.first_sibling_pos
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):   # Ctrl-F
                if self.tree.pos+(app.h-4) <= len(self.tree)-1:
                    if self.tree.cur_depth == self.tree.get_depth(self.tree.pos+(app.h-4)):
                        newpos = self.tree.pos+(app.h-4)
                    else:
                        newpos = self.tree.last_sibling_pos
                else:
                    newpos = self.tree.last_sibling_pos
            elif (ch in (curses.KEY_HOME, 0x01)) or (chext == 1) and (ch == 72):
                newpos = 1
            elif (ch in (curses.KEY_END, 0x05)) or (chext == 1) and (ch == 70):
                newpos = len(self.tree) - 1
            elif ch == curses.KEY_LEFT:
                if self.tree.pos == 0:
                    continue
                newpos = self.tree.parent_pos
            elif ch == curses.KEY_RIGHT:
                new_path = self.tree.to_child()
                if new_path is not None:
                    self.path = new_path
                continue
            elif ch in (10, 13):
                return self.path
            elif ch == curses.KEY_RESIZE:
                curses.doupdate()
                app.resize()
                self.__calculate_dims()
                self.win.resize(self.dims[0], self.dims[1])
                self.win.mvwin(self.dims[2], self.dims[3])
                continue
            elif ch in (ord('q'), ord('Q'), curses.KEY_F10, 0x03):  # Ctrl-C
                return -1
            else:
                continue
            # update
            self.path = self.tree.regenerate_from_pos(newpos)


########################################################################
##### InternalView
class InternalView:
    """View information on full screen"""

    def __init__(self, title, lbuf, center=True):
        self.title = title
        self.prepare_lines(lbuf, center)
        self.init_curses()

    def prepare_lines(self, lbuf, center):
        self.lbuf = [(text2wrap(l, app.w-2).strip(), c) for l, c in lbuf]
        self.nlines = len(lbuf)
        self.large = self.nlines > app.h-2
        if center:
            col_max = max_length([l for l, _ in self.lbuf])
            self.x0, self.y0 = (app.w-col_max)//2, 0 if self.large else (app.h-2-self.nlines)//2
        else:
            self.x0, self.y0 = 1, 0 if self.large else 1
        self.y = 0

    def init_curses(self):
        try:
            win_title = curses.newwin(1, app.w, 0, 0)
            self.win_body = curses.newwin(app.h-2, app.w, 1, 0)
            win_status = curses.newwin(1, app.w, app.h-1, 0)
        except curses.error:
            raise
        win_title.bkgd(app.CLR['header'])
        self.win_body.bkgd(app.CLR['view_white_on_black'])
        win_status.bkgd(app.CLR['statusbar'])
        self.win_body.keypad(1)
        win_title.erase()
        win_status.erase()
        title = text2wrap(self.title, app.w-1).strip()
        win_title.addstr(0, (app.w-length(title))//2, title)
        status = '' if self.large else 'Press any key to continue'
        win_status.addstr(0, (app.w-len(status))//2, status)
        win_title.refresh()
        win_status.refresh()

    def show(self):
        self.win_body.erase()
        for i, (l, c) in enumerate(self.lbuf[self.y:self.y+app.h-2]):
            self.win_body.addstr(self.y0+i, self.x0, l, app.CLR[c])
        self.win_body.refresh()

    def run(self):
        if self.large:
            while True:
                self.show()
                ch = self.win_body.getch()
                if ch in (ord('k'), ord('K'), curses.KEY_UP):
                    self.y = max(self.y-1, 0)
                if ch in (ord('j'), ord('J'), curses.KEY_DOWN):
                    self. y = min(self.y+1, self.nlines-1)
                elif ch in (curses.KEY_HOME, 0x01):
                    self.y = 0
                elif ch in (curses.KEY_END, 0x05):
                    self.y = self.nlines - 1
                elif ch in (curses.KEY_PPAGE, 0x08, 0x02, curses.KEY_BACKSPACE):
                    self.y = max(self.y-app.h+2, 0)
                elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):
                    self.y = min(self.y+app.h-2, self.nlines-1)
                elif ch in (0x1B, ord('q'), ord('Q'), curses.KEY_F3, curses.KEY_F10):
                    break
        else:
            self.show()
            while not self.win_body.getch():
                pass


########################################################################
