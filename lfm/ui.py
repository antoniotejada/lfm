# -*- coding: utf-8 -*-


import errno
import curses
from os import getuid, pardir
from os.path import dirname, exists, join
from datetime import datetime

from preferences import Config, load_colortheme, load_keys, History
from folders import new_folder, is_delete_oldfs
from utils import num2str, length, text2wrap, get_realpath, run_in_background, run_shell, ProcessCommand
from ui_widgets import display_scrollbar, DialogError, DialogConfirm, EntryLine, InternalView
from key_defs import key_bin2str
from actions import do
from common import *


########################################################################
##### Definitions and module variables
colors_table = {'black': curses.COLOR_BLACK,
                'blue': curses.COLOR_BLUE,
                'cyan': curses.COLOR_CYAN,
                'green': curses.COLOR_GREEN,
                'magenta': curses.COLOR_MAGENTA,
                'red': curses.COLOR_RED,
                'white': curses.COLOR_WHITE,
                'yellow': curses.COLOR_YELLOW}

##### Module variables
app, cfg = None, None


########################################################################
##### Main window
class UI:
    def __init__(self, cfg, win, paths1, paths2):
        logging.debug('Create UI')
        self.cfg = cfg
        self.win = win
        self.w = self.h = 0
        self.CLR = dict()
        self.init_curses()
        self.pane1 = Pane(self, paths1)
        self.pane2 = Pane(self, paths2)
        self.statusbar = StatusBar(self)
        self.cli = PowerCLI(self)
        self.focus_pane(self.pane1)
        self.resize()

    def init_curses(self):
        curses.cbreak()
        curses.raw()
        self.win.leaveok(1)
        self.win.keypad(1)
        curses.curs_set(0)
        self.init_colors()
        self.init_keys()
        self.init_history()
        # HACK: ugly hack to inject main app in that module
        import ui_widgets
        ui_widgets.app = self

    def init_colors(self):
        if curses.has_colors():
            try:
                colors = load_colortheme()
            except FileNotFoundError:
                raise
            for i, col in enumerate(colors.keys()):
                fg, bg = colors[col]
                light = fg.endswith('*')
                fg = fg[:-1] if fg.endswith('*') else fg
                bg = bg[:-1] if bg.endswith('*') else bg
                color_fg, color_bg = colors_table[fg], colors_table[bg]
                curses.init_pair(i+1, color_fg, color_bg)
                self.CLR[col] = curses.color_pair(i+1)
                if light:
                    self.CLR[col] = self.CLR[col] | curses.A_BOLD
        else:
            for col in COLOR_ITEMS:
                self.CLR[col] = curses.color_pair(0)

    def init_keys(self):
        try:
            self.keys = load_keys()
        except FileNotFoundError:
            raise

    def init_history(self):
        self.history = History()
        if self.cfg.options.save_history_at_exit:
            try:
                self.history.load()
            except Exception as e:
                return

    def focus_pane(self, pane):
        pane.focus = True
        otherpane = self.pane2 if pane==self.pane1 else self.pane1
        otherpane.focus = False

    @property
    def pane_active(self):
        return self.pane1 if self.pane1.focus else self.pane2

    @property
    def pane_inactive(self):
        return self.pane2 if self.pane1.focus else self.pane1

    def resize(self):
        h, w = self.win.getmaxyx()
        logging.debug('Resize UI: w={}, h={}'.format(w, h))
        self.h, self.w = h, w
        if w == 0 or h == 2:
            return
        if w < MIN_COLUMNS:
            raise LFMTerminalTooNarrow
        self.win.resize(self.h, self.w)
        if self.pane1.mode == PaneMode.full:
            self.pane1.resize(0, 0, h-1, w)
        elif self.pane1.mode == PaneMode.hidden:
            self.pane1.resize(0, 0, h-1, w)
        else:
            self.pane1.resize(0, 0, h-1, w//2)
        if self.pane2.mode == PaneMode.full:
            self.pane2.resize(0, 0, h-1, w)
        elif self.pane2.mode == PaneMode.hidden:
            self.pane2.resize(0, 0, h-1, w)
        else:
            self.pane2.resize(0, w//2, h-1, w//2)
        self.statusbar.resize(h-1, w)
        self.cli.resize(h-1, w)
        self.display()

    def clear_screen(self):
        logging.debug('Clear screen')
        self.pane1.clear()
        self.pane2.clear()
        self.statusbar.clear()
        curses.doupdate()

    def display(self):
        logging.debug('Display UI')
        self.pane1.display()
        self.pane2.display()
        self.display_statusbar_or_powercli()
        self.win.noutrefresh()
        curses.doupdate()

    def display_half(self):
        logging.debug('Display half UI')
        self.pane_active.display()
        self.display_statusbar_or_powercli()
        self.win.noutrefresh()
        curses.doupdate()

    def display_statusbar_or_powercli(self):
        if self.cli.visible:
            self.cli.display()
        else:
            self.statusbar.display()

    def run(self):
        self.display()
        while True:
            ret, extra = self.get_key()
            if ret == RetCode.quit_chdir:
                return extra
            elif ret == RetCode.quit_nochdir:
                return None
            elif ret == RetCode.fix_limits:
                self.pane_active.tab_active.fix_limits()
                self.display_half()
            elif ret == RetCode.full_redisplay:
                self.display()
            elif ret == RetCode.half_redisplay:
                self.display_half()

    def get_key(self):
        self.win.nodelay(False)
        km = KeyModifier.none
        key = self.win.getch()
        if key == 27: # Esc or Alt
            km = KeyModifier.alt
            self.win.nodelay(True)
            key = self.win.getch()
            if key == -1: # Esc
                km, key = KeyModifier.none, 27
        if key == curses.KEY_RESIZE:
            self.resize()
            return RetCode.full_redisplay, None
        key_str = key_bin2str((km, key))
        action = self.keys[(km, key)] if (km, key) in self.keys else None
        logging.debug('Key pressed: {0} [{1:#x}] => {2} => {3} -> {4}'
                      .format(curses.keyname(key), key, str((km, key)), key_str, action if action else '<undefined>'))
        return do(self, action) if action else (RetCode.nothing, None)


########################################################################
##### Pane
class Pane:
    def __init__(self, ui, paths):
        logging.debug('Create Pane')
        self.ui = ui
        self.mode = PaneMode.half
        self.focus = False
        self.tabs = [Tab(p) for p in paths[:MAX_TABS]]
        self.tab_active = self.tabs[0]
        # ui
        try:
            self.win_tabs = curses.newwin(1, 1, 0, 0)
            self.win = curses.newwin(10, 10, 0, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['pane_inactive'])

    def resize(self, y0, x0, h, w):
        logging.debug('Resize Pane: x0={}, y0={}, w={}, h={}'.format(x0, y0, h, w))
        self.x0, self.y0 = x0, y0
        self.w, self.h = w, h
        self.fh = h-4 if self.mode==PaneMode.half else h-1
        self.win_tabs.resize(2, w)
        self.win_tabs.mvwin(y0, x0)
        self.win.resize(h-1, w)
        self.win.mvwin(y0+1, x0)
        try:
            for tab in self.tabs:
                tab.fix_limits()
        except AttributeError:
            pass

    def clear(self):
        self.win.erase()
        self.win_tabs.erase()
        self.win.noutrefresh()
        self.win_tabs.noutrefresh()

    def display(self):
        logging.debug('Display Pane')
        if self.mode == PaneMode.hidden:
            return
        tab = self.tab_active
        CLR = self.ui.CLR
        # tabs
        self.win_tabs.erase()
        self.win_tabs.addstr(0, 0, ' '*self.w, CLR['header'])
        wtab = self.w // MAX_TABS
        for i, t in enumerate(self.tabs):
            pathname = '/' if t.fs.basename=='' else t.fs.basename
            buf = '[' + text2wrap(pathname, wtab-2, start_pct=.5) + ']'
            self.win_tabs.addstr(0, wtab*i, buf, CLR['tab_active' if t==tab else 'tab_inactive'])
        # contens:
        self.win.erase()
        if self.mode == PaneMode.half:
            self.__display_panehalf(tab, CLR)
        elif self.mode == PaneMode.full:
            self.__display_panefull(tab, CLR)
        # refresh
        self.win_tabs.noutrefresh()
        self.win.noutrefresh()

    def __display_panehalf(self, tab, CLR):
        if self.focus:
            attr, attr_path = CLR['pane_active'], CLR['pane_header_path']
        else:
            attr, attr_path = CLR['pane_inactive'], CLR['pane_inactive']
        self.win.attrset(attr)
        # box
        self.win.box()
        self.win.addstr(0, 2, text2wrap(tab.fs.path_str, self.w-5, start_pct=.33, fill=False), attr_path)
        col2 = self.w - 14 # sep between size and date: w - len(mtime) - 2x borders
        col1 = col2 - 8    # sep between filename and size: col2 - len(size) - 1x border
        self.win.addstr(1, 1, 'Name'.center(col1-2)[:col1-2], CLR['pane_header_titles'])
        self.win.addstr(1, col1+2, 'Size', CLR['pane_header_titles'])
        self.win.addstr(1, col2+5, 'Date', CLR['pane_header_titles'])
        if tab.fs.cfg.show_dotfiles:
            self.win.addstr(0, self.w-3, '·', attr)
        if tab.fs.cfg.filters:
            self.win.addstr(0, self.w-2, 'f', attr)
        # files
        fmt = [('type', 1), ('name', col1-2), ('sep', 1), ('size', 7), ('sep', 1), ('mtime', 12)]
        for i in range(self.h-4):
            if i+tab.a >= len(tab.fs):
                break
            f = tab.fs[tab.a+i]
            if self.focus and tab.i == tab.a+i:
                attr = 'cursor_selected' if f in tab.selected else 'cursor'
            else:
                attr = 'selected_files' if f in tab.selected else 'files_' + f.get_type_from_ext(self.ui.cfg.files_ext)
            self.win.addstr(2+i, 1, f.format(fmt), CLR[attr])
        # vertical separators
        self.win.vline(1, col1, curses.ACS_VLINE, self.h-3)
        self.win.vline(1, col2, curses.ACS_VLINE, self.h-3)
        if self.focus:
            self.win.vline(tab.i-tab.a+2, col1, curses.ACS_VLINE, 1, CLR['cursor'])
            self.win.vline(tab.i-tab.a+2, col2, curses.ACS_VLINE, 1, CLR['cursor'])
        # scrollbar
        display_scrollbar(self.win, 2, self.w-1, self.h-4, len(tab.fs), tab.i, tab.a)

    def __display_panefull(self, tab, CLR):
        self.win.attrset(CLR['pane_inactive'])
        # files
        col = self.w - 64 # 1x border
        fmt = [('type', 1), ('mode', 9), ('sep', 2), ('owner', 10), ('sep', 2), ('group', 10), ('sep', 2),
               ('size', 7), ('sep', 2), ('mtime2', 16), ('sep', 2), ('name', col)]
        for i in range(self.h-1):
            if i+tab.a >= len(tab.fs):
                break
            f = tab.fs[tab.a+i]
            if tab.i == tab.a+i:
                attr = 'cursor_selected' if f in tab.selected else 'cursor'
            else:
                attr = 'selected_files' if f in tab.selected else 'files_' + f.get_type_from_ext(self.ui.cfg.files_ext)
            self.win.addstr(i, 0, f.format(fmt, sep=' '), CLR[attr])
        # scrollbar
        display_scrollbar(self.win, 0, self.w-1, self.h-1, len(tab.fs), tab.i, tab.a)

    def change_mode(self, newmode):
        otherpane = self.ui.pane2 if self==self.ui.pane1 else self.ui.pane1
        if self.mode == PaneMode.full:
            otherpane.mode = PaneMode.half
        if newmode == PaneMode.full:
            otherpane.mode = PaneMode.hidden
        self.mode = newmode
        self.ui.resize()

    def refresh(self):
        for tab in self.tabs:
            tab.refresh()

    def insert_new_tab(self, path, lefttab):
        newtab = Tab(path)
        self.tabs.insert(self.tabs.index(lefttab)+1, newtab)
        self.tab_active = newtab

    def close_tab(self, tab):
        idx = self.tabs.index(tab)
        tab.close()
        self.tabs.remove(tab)
        self.tab_active = self.tabs[idx-1]


########################################################################
##### Tab
class Tab:
    def __init__(self, path):
        self.fs = None
        self.history = []
        self.goto_folder(path)

    def __check_rebuild(self):
        if self.fs.vfs:
            rebuild = 1 if app.cfg.options.rebuild_vfs is True else 0
            if app.cfg.confirmations.ask_rebuild_vfs:
                rebuild = DialogConfirm('Rebuild vfs file', self.fs.base_filename, rebuild)
            return rebuild==1
        else:
            return False

    def close(self):
        self.fs.exit(all_levels=True, rebuild=self.__check_rebuild())

    def goto_folder(self, path, delete_vfs_tree=False, files=None):
        """Called when chdir to a new path"""
        oldpath = self.fs.path_str if self.fs else None
        oldfs = self.fs
        try:
            if files: # search vfs
                self.fs = new_folder(path, self.fs, files=files)
            else:
                rebuild = self.__check_rebuild() if is_delete_oldfs(path, self.fs) else False
                self.fs = new_folder(path, self.fs, rebuild_if_exit=rebuild)
            self.fs.cfg.filters = oldfs.cfg.filters if oldfs else ''
        except PermissionError as e:
            logging.warning('ERROR: cannot enter in {}: {}'.format(path, str(e)))
            app.display()
            DialogError('Cannot chdir {}\n{}'.format(path, str(e).split(':', 1)[0]))
            return
        except UserWarning as e:
            logging.warning('ERROR: cannot enter in {}: {}'.format(path, str(e)))
            app.display()
            DialogError('Cannot chdir {}\n{}'.format(path, str(e)))
            return
        except FileNotFoundError:
            logging.warning('ERROR: cannot enter in {}: invalid directory?'.format(path))
            app.display()
            DialogError('Cannot chdir {}\nInvalid directory?'.format(path))
            return
        if delete_vfs_tree:
            oldfs.exit(all_levels=True)
        self.a = self.i = 0
        self.selected = []
        self.refresh(first=True)
        if oldpath and VFS_STRING not in oldpath:
            if oldpath in self.history:
                self.history.remove(oldpath)
            self.history.append(oldpath)
            self.history = self.history[-HISTORY_MAX:]

    def reload(self):
        """Called when contents have changed"""
        try:
            self.fs.load()
        except OSError as err:
            if err.errno == errno.ENOENT: # dir deleted?
                pardir = self.fs.pdir
                while not exists(pardir):
                    pardir = dirname(pardir)
                self.goto_folder(pardir)
        self.refresh()

    def refresh(self, first=False):
        """Called when config or filters have changed"""
        if not first:
            oldi = self.i
            oldf = self.fs[self.i].name
            oldselected = [f.name for f in self.selected]
        self.fs.cfg.fill_with_app(cfg)
        self.fs.refresh()
        self.n = len(self.fs)
        i = 0 if first else self.fs.pos(oldf)
        self.i = oldi if i==-1 else i
        self.a = divmod(self.i, self.n)[0] * self.n
        if not first:
            self.fix_limits()
            self.selected = list(filter(None, [self.fs.lookup(f) for f in oldselected]))

    def fix_limits(self):
        self.i = max(0, min(self.i, self.n-1))
        self.a = int(self.i//app.pane_active.fh * app.pane_active.fh)

    def focus_file(self, filename):
        i = self.fs.pos(filename)
        if i != -1:
            self.i = i
            self.fix_limits()

    @property
    def dirname(self):
        return self.fs.pdir

    @property
    def current_filename(self):
        return self.fs[self.i].name

    @property
    def current_filename_full(self):
        return join(self.fs.pdir, self.fs[self.i].name)

    @property
    def current(self):
        return self.fs[self.i]

    @property
    def selected_or_current(self):
        if len(self.selected) == 0:
            cur = self.fs[self.i]
            return list() if cur.name==pardir else [cur]
        else:
            return self.selected

    @property
    def selected_or_current2(self):
        return self.selected if self.selected else [self.fs[self.i]]


########################################################################
##### Statusbar
class StatusBar:
    def __init__(self, ui):
        logging.debug('Create StatusBar')
        self.ui = ui
        try:
            self.win = curses.newwin(1, 10, 1, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['statusbar'])

    def resize(self, y0, w):
        logging.debug('Resize StatusBar: y0={}, w={}'.format(y0, w))
        self.y0, self.w = y0, w
        self.win.resize(1, w)
        self.win.mvwin(y0, 0)

    def clear(self):
        self.win.erase()
        self.win.noutrefresh()

    def display(self):
        logging.debug('Display StatusBar')
        self.win.erase()
        tab = self.ui.pane_active.tab_active
        if len(tab.selected) > 0:
            if self.w >= 45:
                size = sum([f.size for f in tab.selected])
                self.win.addstr('    %s bytes in %d files' % (num2str(size), len(tab.selected)))
        else:
            if self.w >= 80:
                s = 'File: %4d of %-4d' % (tab.i+1, tab.n)
                if tab.fs.cfg.filters:
                    s+= '  [%d filtered]' % tab.fs.nfiltered
                self.win.addstr(s)
                filename = text2wrap(get_realpath(tab), self.w-20-len(s), fill=False)
                self.win.addstr(0, len(s)+4, 'Path: ' + filename)
        if self.w > 10:
            try:
                self.win.addstr(0, self.w-8, 'F1=Help')
            except:
                pass
        self.win.refresh()

    def show_message(self, text):
        self.win.erase()
        self.win.addstr(0, 1, text2wrap(text, self.w-2, fill=False))
        self.win.refresh()


########################################################################
##### PowerCLI
class PowerCLI:
    RUN_NORMAL, RUN_BACKGROUND, RUN_NEEDCURSESWIN = range(3)

    def __init__(self, ui):
        logging.debug('Create PowerCLI')
        self.ui = ui
        self.visible = self.running = False
        try:
            self.win = curses.newwin(1, 10, 1, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['powercli_text'])
        self.entry, self.text, self.pos = None, '', 0

    def toggle(self):
        if self.visible:
            self.visible = self.running = False
        else:
            self.visible, self.running = True, False

    def resize(self, y0, w):
        logging.debug('Resize PowerCLI: y0={}, w={}'.format(y0, w))
        self.y0, self.w = y0, w
        self.win.resize(1, w)
        self.win.mvwin(y0, 0)

    def display(self):
        if self.running:
            return
        logging.debug('Display PowerCLI')
        tab = self.ui.pane_active.tab_active
        self.win.erase()
        path = text2wrap(tab.fs.path_str, self.ui.w//6, start_pct=0, fill=False)
        prompt = '[{}]{} '.format(path, '#' if getuid()==0 else '$')
        lprompt = length(prompt)
        self.win.addstr(0, 0, prompt, self.ui.CLR['powercli_prompt'])
        self.win.noutrefresh()
        curses.curs_set(1)
        self.running = True
        self.entry = EntryLine(self, self.w-lprompt, self.y0, lprompt, self.text,
                               history=self.ui.history['cli'][:], is_files=True, cli=True)
        self.entry.pos = self.pos
        self.entry.show()
        ans = self.entry.manage_keys()
        if ans == -1:           # Ctrl-C
            cmd, self.text, self.pos = None, '', 0
        elif ans == -2:           # Ctrl-X
            cmd, self.text, self.pos = None, self.entry.text, self.entry.pos
        elif ans == 10:         # return
            cmd, self.text, self.pos = self.entry.text.strip(), '', 0
            if cmd:
                self.execute(cmd)
        else:
            raise ValueError
        curses.curs_set(0)
        self.visible = False
        self.ui.display()

    def execute(self, cmd):
        self.ui.history.append('cli', cmd)
        logging.debug('PowerCLI Execute: |{}|'.format(cmd))
        selected = [f for f in self.ui.pane_active.tab_active.selected_or_current2]
        if cmd[-1] == '&':
            mode, cmd = PowerCLI.RUN_BACKGROUND, cmd[:-1].strip()
        elif cmd[-1] == '$':
            mode, cmd = PowerCLI.RUN_NEEDCURSESWIN, cmd[:-1].strip()
        else:
            mode = PowerCLI.RUN_NORMAL
        for f in selected:
            try:
                cmd2 = self.__replace_cli(cmd, f)
            except Exception as err:
                log.warning('Cannot execute PowerCLI command: {}\n{}'.format(cmd2, str(err)))
                DialogError('Cannot execute PowerCLI command:\n  {}\n\n{}'.format(cmd2, str(err)))
            else:
                if self.__run(cmd2, self.ui.pane_active.tab_active.dirname, mode) == -1:
                    self.ui.display()
                    if DialogConfirm('Error running PowerCLI', 'Do you want to stop now?') == 1:
                        break
        self.ui.pane_active.tab_active.selected = []

    def __replace_cli(self, cmd, f):
        # prepare variables
        tab = self.ui.pane_active.tab_active
        filename = f.name
        cur_directory = tab.dirname
        other_directory = self.ui.pane_inactive.tab_active.dirname
        fullpath = f.pfile
        filename_noext = f.name_noext
        ext = f.ext
        all_selected = [s.name for s in tab.selected]
        all_files = [elm for elm in tab.fs.get_filenames() if elm is not pardir]
        try:
            selection_idx = all_selected.index(filename)+1
        except ValueError:
            selection_idx = 0
        tm = datetime.fromtimestamp(f.mtime)
        ta = datetime.fromtimestamp(f.stat.st_atime)
        tc = datetime.fromtimestamp(f.stat.st_ctime)
        tnow = datetime.now()
        dm = tm.date()
        da = ta.date()
        dc = tc.date()
        dnow = tnow.date()
        # conversion table
        lcls = {'f': filename, 'v': filename, 'F': fullpath,
                'E': filename_noext, 'e': ext,
                'p': cur_directory, 'o': other_directory,
                's': all_selected, 'a': all_files, 'i': selection_idx,
                'dm': dm, 'da': da, 'dc': dc, 'dn': dnow,
                'tm': tm, 'ta': ta, 'tc': tc, 'tn': tnow}
        for k, bmk in self.ui.cfg.bookmarks.items():
            lcls['b{}'.format(k)] = bmk
        # and replace, first python code, and then variables
        cmd = self.__replace_python(cmd, lcls)
        cmd = self.__replace_variables(cmd, lcls)
        return cmd

    def __replace_python(self, cmd, lcls):
        lcls = dict([('__lfm_{}'.format(k), v) for k, v in lcls.items()])
        # get chunks
        chunks, st = {}, 0
        while True:
            i = cmd.find('{', st)
            if i == -1:
                break
            j = cmd.find('}', i+1)
            if j == -1:
                raise SyntaxError('{ at %d position has not ending }' % i)
            else:
                chunks[(i+1, j)] = cmd[i+1:j].replace('$', '__lfm_')
                st = j + 1
        # evaluate
        if chunks == {}:
            return cmd
        buf, st = '', 0
        for i, j in sorted(chunks.keys()):
            buf += cmd[st:i-1]
            try:
                translated = eval(chunks[(i, j)], {}, lcls)
            except Exception as err:
                raise SyntaxError(str(err).replace('__lfm_', '$'))
            buf += translated
            st = j+1
        buf += cmd[st:]
        return buf

    def __replace_variables(self, cmd, lcls):
        for k, v in lcls.items():
            if k in ('i', ):
                cmd = cmd.replace('${}'.format(k), str(v))
            elif k in ('dm', 'da', 'dc', 'dn', 'tm', 'ta', 'tc', 'tn'):
                cmd = cmd.replace('${}'.format(k), str(v).split('.')[0])
            elif k in ('s', 'a'):
                cmd = cmd.replace('${}'.format(k), ' '.join(['"{}"'.format(f) for f in v]))
            else:
                cmd = cmd.replace('${}'.format(k), v)
        return cmd

    def __run(self, cmd, path, mode):
        curses.curs_set(0)
        if mode == PowerCLI.RUN_NEEDCURSESWIN:
            run_shell(cmd, path)
            st, msg, err = 0, '', ''
        elif mode == PowerCLI.RUN_BACKGROUND:
            run_in_background(cmd, path)
            st, msg, err = 0, '', ''
        else: # PowerCLI.RUN_NORMAL
            st, msg, err = ProcessCommand('Executing PowerCLI', cmd, cmd, path).run()
        if err:
            log.warning('Error running PowerCLI command: {}\n{}'.format(cmd, str(err)))
            DialogError('Error running PowerCLI command:\n  {}\n\n{}'.format(cmd, str(err)))
        if st != -100 and msg:
            if self.ui.cfg.options.show_output_after_exec:
                if DialogConfirm('Executing PowerCLI', 'Show output?', 1) == 1:
                    lst = [(l, 'view_white_on_black') for l in msg.split('\n')]
                    InternalView('Output of: {}'.format(cmd), lst, center=False).run()
        return st

########################################################################
##### Main
def init_config(use_wide_chars):
    global cfg
    cfg = Config()
    cfg.load()
    # HACK: ugly hack to inject option in that module
    import utils
    utils.use_wide_chars = True if use_wide_chars else cfg.options.use_wide_chars
    log.info('Support wide chars: {}'.format(utils.use_wide_chars))
    return cfg


def launch_ui(win, path1, path2, use_wide_chars):
    global app
    cfg = init_config(use_wide_chars)
    try:
        app = UI(cfg, win, [path1], [path2])
        ret = app.run()
    except LFMTerminalTooNarrow as e:
        DialogError('Terminal too narrow to show contents.\nIt should have {} columns at mininum.'.format(MIN_COLUMNS))
        return None
    if app.cfg.options.save_configuration_at_exit:
        try:
            app.cfg.save()
        except Exception as e:
            DialogError('Cannot save configuration file\n{}'.format(str(e)))
    if app.cfg.options.save_history_at_exit:
        try:
            app.history.save()
        except Exception as e:
            DialogError('Cannot save history file\n{}'.format(str(e)))
    return ret


def run_app(path1, path2, use_wide_chars):
    return curses.wrapper(launch_ui, path1, path2, use_wide_chars)


########################################################################
