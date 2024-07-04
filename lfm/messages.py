import sys
import os.path
import curses
import files


# global
historic = []


##################################################
##################################################
class CommonWindow:
    """A superclass for error and win windows"""
    
    def __init__(self, title, text, br_att, br_bg, bd_att, bd_bg):
        text = text.replace('\t', ' ' * 4)
        lines = text.split('\n')
        length = 0
        for l in lines:
            if len(l) > length:
                length = len(l)
        h = min(len(lines) + 4, curses.LINES - 2)
        w = min(max(length+6, 27+4), curses.COLS - 2)
        try:
            self.border = curses.newwin(h, w, 
                                        (curses.LINES-h) / 2,
                                        (curses.COLS-w) / 2)
            self.body = curses.newwin(h-2, w-4,
                                      (curses.LINES-h)/2 + 1,
                                      (curses.COLS-w)/2 + 2)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        self.border.attrset(br_att)
        self.border.bkgdset(br_bg)
        self.body.attrset(bd_att)
        self.body.bkgdset(bd_bg)
        self.border.erase()
        self.body.erase()
        self.border.box(0, 0)
        self.border.addstr(0, (w-len(title)-2)/2, ' ' + title + ' ')
        self.body.addstr(1, 1, text)
        self.border.addstr(h-1, (w-27)/2, ' Press any key to continue ')
        self.border.refresh()
        self.body.refresh()
        self.border.keypad(1)

    def run(self):
        while not self.border.getch():
            pass


##################################################
##################################################
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


##################################################
##################################################
def win(title, text):
    """show a message window"""

    CommonWindow(title, text,
                 curses.color_pair(1) | curses.A_BOLD,
                 curses.color_pair(1),
                 curses.color_pair(4),
                 curses.color_pair(4)).run()


##################################################
##################################################
def notyet(title):
    """show a not-yet-implemented message"""

    CommonWindow(title,
                 'Sorry, but this function\n is not implemented yet!',
                 curses.color_pair(1) | curses.A_BOLD,
                 curses.color_pair(1),
                 curses.color_pair(4),
                 curses.color_pair(4)).run()


##################################################
##################################################
def get_a_key(title, question):
    """show a window returning key pressed"""

    question = question.replace('\t', ' ' * 4)
    lines = question.split('\n')
    length = 0
    for l in lines:
        if len(l) > length:
            length = len(l)
    h = min(len(lines) + 4, curses.LINES - 2)
    w = min(length + 4, curses.COLS - 2)
    try:
        border = curses.newwin(h, w, 
                               (curses.LINES-h) / 2, (curses.COLS-w) / 2)
        label = curses.newwin(1, len(title) + 2,
                              (curses.LINES-h) / 2,
                              (curses.COLS-len(title)-2) / 2)
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    border.attrset(curses.color_pair(1))
    border.bkgdset(curses.color_pair(1))
    label.attrset(curses.color_pair(1) | curses.A_BOLD)
    label.bkgdset(curses.color_pair(1))
    border.erase()
    label.erase()
    border.box(0, 0)
    row = 2
    for l in lines:
        border.addstr(row, 2, l)
        row += 1
    label.addstr(' %s' % title)
    border.refresh()
    label.refresh()

    border.keypad(1)
    while 1:
        ch = border.getch()
        if ch in [0x03]:       # Ctrl-C
            return -1
        elif 0x01 <= ch <= 0xFF:
            return ch
        else:
            curses.beep()


##################################################
##################################################
def confirm(title, question, default = 0):
    """show a yes/no window, returning 1/0"""

    h = 5
    w = min(max(34, len(question)+5), curses.COLS - 2)
    try:
        border = curses.newwin(h, w, 
                               (curses.LINES-h) / 2, (curses.COLS-w) / 2)
        label = curses.newwin(1, len(title) + 2,
                              (curses.LINES-h) / 2,
                              (curses.COLS-len(title)-2) / 2)
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    border.attrset(curses.color_pair(1))
    border.bkgdset(curses.color_pair(1))
    label.attrset(curses.color_pair(1) | curses.A_BOLD)
    label.bkgdset(curses.color_pair(1))

    border.erase()
    label.erase()
    border.box(0, 0)
    border.addstr(1, 2 , '%s?' % question)
    label.addstr(' %s' % title)
    border.refresh()
    label.refresh()

    row = (curses.LINES - h) / 2 + 3
    col = (curses.COLS - w) / 2
    col1 = col + w/5 + 1
    col2 = col + w*4/5 - 6

    border.keypad(1)
    answer = default
    while 1:
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
        
        ch = border.getch()
        if ch in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT,
                  curses.KEY_RIGHT, 9]:
            if answer:
                answer = 0
            else:
                answer = 1
        elif ch in ['Y', 'y']:
            return 1
        elif ch in ['N', 'n', 0x1B, 0x03]:
            return 0
        elif ch in [0x03]:          # Ctrl-C
            return -1
        elif ch in [10, 13]:        # enter
            return answer
        else:
            curses.beep()

    return answer


##################################################
##################################################
def confirm_all(title, question, default = 0):
    """show a yes/no window, returning 1/0"""

    h = 5
    w = min(max(34, len(question)+5), curses.COLS - 2)
    try:
        border = curses.newwin(h, w, 
                               (curses.LINES-h) / 2, (curses.COLS-w) / 2)
        label = curses.newwin(1, len(title) + 2,
                              (curses.LINES-h) / 2,
                              (curses.COLS-len(title)-2) / 2)
    except curses.error:
        print 'Can\'t create window'
        sys.exit(-1)
    border.attrset(curses.color_pair(1))
    border.bkgdset(curses.color_pair(1))
    label.attrset(curses.color_pair(1) | curses.A_BOLD)
    label.bkgdset(curses.color_pair(1))

    border.erase()
    label.erase()
    border.box(0, 0)
    border.addstr(1, 2 , '%s?' % question)
    label.addstr(' %s' % title)
    border.refresh()
    label.refresh()

    row = (curses.LINES - h) / 2 + 3
    col = (curses.COLS - w) / 2
    col1 = col + w/5 - 2
    col2 = curses.COLS/2 - 3
    col3 = col + w*4/5 - 3

    border.keypad(1)
    answer = default
    while 1:
        if answer == 1:
            attr_yes = curses.color_pair(9) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
        elif answer == 2:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(9) | curses.A_BOLD
            attr_no = curses.color_pair(1) | curses.A_BOLD
        else:
            attr_yes = curses.color_pair(1) | curses.A_BOLD
            attr_all = curses.color_pair(1) | curses.A_BOLD
            attr_no = curses.color_pair(9) | curses.A_BOLD
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ Yes ]', attr_yes)
        btn.refresh(0, 0, row, col1, row + 1, col1 + 6)
        btn = curses.newpad(1, 8)
        btn.addstr(0, 0, '[ All ]', attr_all)
        btn.refresh(0, 0, row, col2, row + 1, col2 + 6)
        btn = curses.newpad(1, 7)
        btn.addstr(0, 0, '[ No ]', attr_no)
        btn.refresh(0, 0, row, col3, row + 1, col3 + 5)
        
        ch = border.getch()
        if ch in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT,
                  curses.KEY_RIGHT, 9]:
            if answer == 1:
                answer = 2
            elif answer == 2:
                answer = 0
            else:
                answer = 1
        elif ch in ['Y', 'y']:
            return 1
        elif ch in ['A', 'a']:
            return 2
        elif ch in ['N', 'n', 0x1B]:
            return 0
        elif ch in [0x03]:          # Ctrl-C
            return -1
        elif ch in [10, 13]:        # enter
            return answer
        else:
            curses.beep()

    return answer


##################################################
##################################################
class SelectItem:
    """A window to select an item"""

    def __init__(self, entries, y0, x0):
        h = (curses.LINES - 1) - (y0 + 1) + 1
        w = min(max(map(len, entries)), curses.COLS/2) + 4
        try:
            self.win = curses.newwin(h, w, y0, x0)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        self.win.keypad(1)
        curses.curs_set(0)
        self.win.attrset(curses.color_pair(4))
        self.win.bkgdset(curses.color_pair(4))

        self.entries = entries
        self.entry_i = 0
        

    def show(self):
        self.win.erase()
        self.win.attrset(curses.color_pair(4))
        self.win.refresh()
        self.win.box(0, 0)
        y, x = self.win.getbegyx()
        h, w = self.win.getmaxyx()
        entry_a = self.entry_i / (h-2) * (h-2)
        for i in range(h-2):
            try:
                line = self.entries[entry_a + i]
            except IndexError:
                line = ''
            if len(line) > w - 2:
                if (w - 2) % 2 == 0:     # even
                    line = line[:(w-2)/2] + '~' + line[-(w-2)/2+2:]
                else:                    # odd
                    line = line[:(w-2)/2+1] + '~' + line[-(w-2)/2+2:]
            if line != '':
                self.win.addstr(i+1, 2, line, curses.color_pair(4))
        self.win.refresh()
        # cursor
        cursor = curses.newpad(1, w - 2)
        cursor.attrset(curses.color_pair(1) | curses.A_BOLD)
        cursor.bkgdset(curses.color_pair(1))
        cursor.erase()
        line = self.entries[self.entry_i]
        if len(line) > w - 2:
            if (w - 2) % 2 == 0:         # even
                line = line[:(w-2)/2] + '~' + line[-(w-2)/2+2:]
            else:                        # odd
                line = line[:(w-2)/2+1] + '~' + line[-(w-2)/2+2:]
        cursor.addstr(0, 1, line, curses.color_pair(1) | curses.A_BOLD)
        y += 1; x += 1
        cursor.refresh(0, 0, y + self.entry_i % (h - 2),
                       x, y + self.entry_i % (h - 2), x + w - 3)
        # scrollbar
        if len(self.entries) > h:
            n = (h-2) * (h-2) / len(self.entries)
            if n == 0:
                n = 1
            a = self.entry_i /(h-2) * (h-2)
            y0 = a * (h-2) / len(self.entries)
            if y0 < 0:
                y0 = 0
            elif y0 + n > (h-2):
                y0 = (h-2) - n
        else:
            y0 = 0
            n = 0
        self.win.vline(y0 + 1, w - 1, curses.ACS_CKBOARD, n)
        if entry_a != 0:
            self.win.vline(1, w - 1, '^', 1)
            if n == 1 and (y0 + 1 == 1):
                self.win.vline(2, w - 1, curses.ACS_CKBOARD, n)
        if len(self.entries) - 1 > entry_a + h - 3:
            self.win.vline(h - 2, w - 1, 'v', 1)
            if n == 1 and (y0 + 1 == h - 2):
                self.win.vline(h - 3, w - 1, curses.ACS_CKBOARD, n)


    def manage_keys(self):
        h, w = self.win.getmaxyx()
        while 1:
            self.show()
            ch = self.win.getch()
            if ch in [0x03, ord('q'), ord('Q')]:       # Ctrl-C
                return -1
            elif ch in [curses.KEY_UP, ord('p'), ord('P')]:
                if self.entry_i != 0:
                    self.entry_i -= 1
            elif ch in [curses.KEY_DOWN, ord('n'), ord('n')]:
                if self.entry_i != len(self.entries) - 1:
                    self.entry_i += 1
            elif ch in [curses.KEY_PPAGE, curses.KEY_BACKSPACE, 0x08, 0x10]:
                if self.entry_i < (h - 3):
                    self.entry_i = 0
                else:
                    self.entry_i -= (h - 2)
            elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:
                if self.entry_i + (h-2) > len(self.entries) - 1:
                    self.entry_i = len(self.entries) - 1
                else:
                    self.entry_i += (h - 2)
            elif ch in [curses.KEY_HOME, 72, 348]:
                self.entry_i = 0
            elif ch in [curses.KEY_END, 70, 351]:
                self.entry_i = len(self.entries) - 1
            elif ch in [0x13]:     # Ctrl-S
                theentries = self.entries[self.entry_i:]
                ch2 = self.win.getkey()
                for e in theentries:
                    if e.find(ch2) == 0:
                        break
                else:
                    continue
                self.entry_i = self.entries.index(e)
            elif ch in [10, 13]:   # enter
                return self.entries[self.entry_i]
            else:
                curses.beep()


    def run(self):
        selected = self.manage_keys()
        try:         # some terminals don't allow '2'
            curses.curs_set(2)
        except:
            curses.curs_set(1)
        return selected


##################################################
##################################################
class Yes_No_Buttons:
    """Yes/No buttons"""

    def __init__(self, w, h, d):
        self.row = (curses.LINES - h) / 2 + 4 + d
        col = (curses.COLS - w) / 2
        self.col1 = col + w/5 + 1
        self.col2 = col + w*4/5 - 6
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
        while 1:
            ch = tmp.getch()
            if ch in [0x03]:            # Ctrl-C
                return -1
            elif ch in [ord('\t')]:
                return ord('\t')
            elif ch in [10, 13]:        # enter
                if self.active == 1:
                    return 10
                else:
                    return -1
            else:
                curses.beep()


##################################################
##################################################
class EntryLine:
    """An entry line to enter a dir. or file, a pattern, ..."""

    def __init__(self, w, h, x, y, text, with_historic, with_complete,
                 basepath, curpath):
        try:
            self.entry = curses.newwin(1, w - 4 + 1, x, y)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        self.entry.attrset(curses.color_pair(11) | curses.A_BOLD)
        self.entry.keypad(1)

        self.entry_width = w - 4
        self.text = text
        self.basepath = basepath
        self.curpath = curpath
        self.pos = len(self.text)
        self.ins = 1

        self.with_complete = with_complete
        self.with_historic = with_historic
        if self.with_historic:
            self.historic = historic[:]
            self.historic_i = len(self.historic)


    def show(self):
        text = self.text
        pos = self.pos
        ew = self.entry_width
        if pos < ew:
            relpos = pos
            if len(text) < ew:
                textstr = text + ' ' * (ew - len(text))
            else:
                textstr = text[:ew]
        else:
            if pos > len(text) - (ew-1):
                relpos = ew - 1 - (len(text) - pos)
                textstr = text[len(text)-ew+1:] + ' '
            else:
                relpos = pos - pos/ew*ew
                textstr = text[pos/ew*ew:pos/ew*ew+ew]
        self.entry.bkgdset(curses.color_pair(1))
        self.entry.erase()
        self.entry.addstr(textstr, curses.color_pair(11) | curses.A_BOLD)
        self.entry.move(0, relpos)
        self.entry.bkgdset(curses.color_pair(1))
        self.entry.refresh()


    def manage_keys(self):
        while 1:
            self.show()
            ch = self.entry.getch()            
#              print 'key: \'%s\' <=> %c <=> 0x%X <=> %d' % \
#                    (curses.keyname(ch), ch & 255, ch, ch)
            if ch == 0x1B:                # to avoid extra chars input
                ch = self.entry.getch()
            elif ch in [0x03]:            # Ctrl-C
                return -1
            elif ch in [curses.KEY_UP]:
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
            elif ch in [curses.KEY_DOWN]:
                if self.with_historic:
                    if self.historic_i < len(self.historic) - 1:
                        self.historic_i += 1
                        self.text = self.historic[self.historic_i]
                        self.pos = len(self.text)
                else:
                    continue                
            elif ch in [ord('\t')]:      # tab
                return ord('\t')
            elif ch in [10, 13]:         # enter
                return 10
            elif ch in [0x14]:           # Ctrl-T
                if self.with_complete:
                    entries = files.complete(self.text, self.basepath,
                                             self.curpath)
                    if not entries:
                        curses.beep()
                        continue
                    elif len(entries) == 1:
                        selected = entries.pop()
                    else:
                        y, x = self.entry.getbegyx()
                        selected = SelectItem(entries, y + 1, x - 2).run()
                    if selected != -1:
                        self.text = files.join(self.text, selected)
                        self.pos = len(self.text)
                    return 0x14                        
                else:
                    continue
            # chars and edit keys
            elif ch in [0x17]:          # Ctrl-W
                if self.text == None or self.text == '':
                    continue
                text = self.text
                if text == os.sep:
                    text = ''
                else:
                    if text[len(text) - 1] == os.sep:
                        text = os.path.dirname(text)
                    text = os.path.dirname(text)
                    if text != '' and text != os.sep:
                        text += os.sep
                # hack to refresh if blank entry
                self.text = ' ' * self.entry_width
                self.entry.bkgdset(curses.color_pair(11))
                self.entry.erase()
                self.entry.addstr(self.text, curses.color_pair(11) | curses.A_BOLD)
                self.entry.refresh()
                self.text = text
                self.pos = len(self.text)
            elif ch in [curses.KEY_IC]: # insert
                if self.ins:
                    self.ins = 0
                else:
                    self.ins = 1                    
            elif ch in [curses.KEY_HOME, 72, 348]:      # home
                self.pos = 0
            elif ch in [curses.KEY_END, 70, 351]:       # end
                self.pos = len(self.text)
            elif ch in [curses.KEY_LEFT] and self.pos > 0:
                self.pos -= 1
            elif ch in [curses.KEY_RIGHT] and self.pos < len(self.text):
                self.pos += 1
            elif ch in [8, curses.KEY_BACKSPACE] and len(self.text) > 0 and \
                 self.pos > 0:    # del
                self.text = self.text[:self.pos-1] + self.text[self.pos:]
                self.pos -= 1
            elif ch in [curses.KEY_DC] and self.pos < len(self.text):  # supr
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


##################################################
##################################################
class Entry:
    """An entry window to enter a dir. or file, a pattern, ..."""

    def __init__(self, title, help, path = '', with_historic = 1,
                 with_complete = 1, basepath = '', curpath = ''):
        h = 6
        w = min(max(34, len(help)+5), curses.COLS - 2)
        try:
            border = curses.newwin(h, w, 
                                   (curses.LINES-h) / 2, (curses.COLS-w) / 2)
            label = curses.newwin(1, len(title) + 2,
                                  (curses.LINES-h) / 2,
                                  (curses.COLS-len(title)-2) / 2)
            self.entry = EntryLine(w, h,
                                   (curses.LINES-h) / 2 + 2,
                                   (curses.COLS-w+4) / 2,
                                   path, with_historic, with_complete,
                                   basepath, curpath)
            self.btns = Yes_No_Buttons(w, h, 0)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        border.attrset(curses.color_pair(1))
        border.bkgdset(curses.color_pair(1))
        label.attrset(curses.color_pair(1) | curses.A_BOLD)
        label.bkgdset(curses.color_pair(1))
        border.erase()
        label.erase()
        border.box(0, 0)
        border.addstr(1, 2 , '%s:' % help)
        label.addstr(' %s' % title)
        border.refresh()
        label.refresh()

        self.with_historic = with_historic
        self.active_entry = self.entry
        self.active_entry_i = 0  # entry


    def run(self):
        self.entry.entry.refresh() # needed to avoid a problem with blank paths
        self.entry.show()
        self.btns.show()
        try:         # some terminals don't allow '2'
            curses.curs_set(2)
        except:
            curses.curs_set(1)

        answer = 1
        quit = 0
        while not quit:
            self.btns.show()
            if self.active_entry_i == 0:
                ans = self.active_entry.manage_keys()
            else:
                ans = self.btns.manage_keys()
            if ans == -1:              # Ctrl-C
                quit = 1
                answer = 0
            elif ans == ord('\t'):     # tab
                self.active_entry_i += 1
                if self.active_entry_i > 2:
                    self.active_entry_i = 0
                if self.active_entry_i == 0:
                    self.active_entry = self.entry
                    self.btns.active = 0
                    try:         # some terminals don't allow '2'
                        curses.curs_set(2)
                    except:
                        curses.curs_set(1)
                elif self.active_entry_i == 1:
                    self.btns.active = 1
                    curses.curs_set(0)
                    answer = 1
                else:
                    self.btns.active = 2
                    curses.curs_set(0)
                    answer = 0
            elif ans == 0x14:            # Ctrl-T
                # this is a hack, we need to return to refresh Entry
                path = []
                path.append(self.entry.text)
                return path
            elif ans == 10:              # return values
                quit = 1
                answer = 1

        curses.curs_set(0)
        if answer:
            # save new historic entries
            if self.with_historic:
                if self.entry.text != None and self.entry.text != '':
                    if len(historic) < 100:
                        historic.append(self.entry.text)
                    else:
                        historic.reverse()
                        historic.pop()
                        historic.reverse()
                        historic.append(self.entry.text)
            return self.entry.text
        else:
            return


##################################################
##################################################
class DoubleEntry:
    """An entry window to enter 2 dirs. or files, patterns, ..."""

    def __init__(self, title, help1 = '', path1 = '',
                 with_historic1 = 1, with_complete1 = 1,
                 basepath1 = '', curpath1 = '',
                 help2 = '', path2 = '',
                 with_historic2 = 1, with_complete2 = 1,
                 basepath2 = '', curpath2 = '', active_entry = 0):
        h = 9
        w = min(max(34, max(len(help1), len(help2)) + 5), curses.COLS - 2)
        try:
            border = curses.newwin(h, w, 
                                   (curses.LINES-h)/2-1, (curses.COLS-w) / 2)
            label = curses.newwin(1, len(title) + 2,
                                  (curses.LINES-h) / 2 - 1,
                                  (curses.COLS-len(title)-2) / 2)
            self.entry1 = EntryLine(w, h,
                                    (curses.LINES-h) / 2 + 1,
                                    (curses.COLS-w+4) / 2,
                                    path1, with_historic1, with_complete1,
                                    basepath1, curpath1)
            self.entry2 = EntryLine(w, h,
                                    (curses.LINES-h) / 2 + 4,
                                    (curses.COLS-w+4) / 2,
                                    path2, with_historic2, with_complete2,
                                    basepath2, curpath2)
            self.btns = Yes_No_Buttons(w, h, 2)
        except curses.error:
            print 'Can\'t create window'
            sys.exit(-1)
        border.attrset(curses.color_pair(1))
        border.bkgdset(curses.color_pair(1))
        label.attrset(curses.color_pair(1) | curses.A_BOLD)
        label.bkgdset(curses.color_pair(1))
        border.erase()
        label.erase()
        border.box(0, 0)
        border.addstr(1, 2 , '%s:' % help1)
        border.addstr(4, 2 , '%s:' % help2)
        label.addstr(' %s' % title)
        border.refresh()
        label.refresh()

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
        try:         # some terminals don't allow '2'
            curses.curs_set(2)
        except:
            curses.curs_set(1)

        answer = 1
        quit = 0
        while not quit:
            self.btns.show()
            if self.active_entry_i in [0, 1]:
                ans = self.active_entry.manage_keys()
            else:
                ans = self.btns.manage_keys()
            if ans == -1:      # Ctrl-C
                quit = 1
                answer = 0
            elif ans == ord('\t'):     # tab
                self.active_entry_i += 1
                if self.active_entry_i > 3:
                    self.active_entry_i = 0
                if self.active_entry_i == 0:
                    self.active_entry = self.entry1
                    self.btns.active = 0
                    try:         # some terminals don't allow '2'
                        curses.curs_set(2)
                    except:
                        curses.curs_set(1)
                elif self.active_entry_i == 1:
                    self.active_entry = self.entry2
                    self.btns.active = 0
                    try:         # some terminals don't allow '2'
                        curses.curs_set(2)
                    except:
                        curses.curs_set(1)
                elif self.active_entry_i == 2:
                    self.btns.active = 1
                    curses.curs_set(0)
                    answer = 1
                else:
                    self.btns.active = 2
                    curses.curs_set(0)
                    answer = 0
            elif ans == 0x14:            # Ctrl-T
                # this is a hack, we need to return to refresh Entry
                path = []
                path.append(self.entry1.text)
                path.append(self.entry2.text)
                path.append(self.active_entry_i)
                return path
            elif ans == 10:    # return values
                quit = 1
                answer = 1

        curses.curs_set(0)
        if answer:
            # save new historic entries
            if self.with_historic:
                for text in self.entry1.text, self.entry2.text:
                    if text != None and text != '':
                        if len(historic) < 100:
                            historic.append(text)
                        else:
                            historic.reverse()
                            historic.pop()
                            historic.reverse()
                            historic.append(text)
            return self.entry1.text, self.entry2.text
        else:
            return None, None

